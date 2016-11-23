import json

import PIL
import time
import thread
import random
import numpy as np
from net import Q
import chainer
from chainer import functions as F
from chainer import cuda, Variable, optimizers, serializers
from PIL import Image
from agent import Agent

latent_size = 256
gamma = 0.99
batch_size = 64

args_gpu = -1 # GPU ID (negative value indicates CPU)
args_input = None #input model file path without extension
args_output = 'model/' # output model file path without extension
args_interval = 100 # interval of capturing (ms)
args_random = 0.2 # randomness of play
args_pool_size = 50000 # number of frames of memory pool size
args_random_reduction = 0.000002 # reduction rate of randomness
args_min_random = 0.1 # minimum randomness of play
args_train_term = 4 # training term size
args_train_term_increase = 0.00002 # increase rate of training term size
args_max_train_term = 32 # maximum training term size
args_update_target_interval = 2000 # interval to update target Q function of Double DQN

interval = args_interval / 1000.0
update_target_interval = args_update_target_interval
train_width = 160
train_height = 120
random.seed()

agent = Agent()

gpu_device = None
xp = np
q = Q(width=train_width, height=train_height, latent_size=latent_size, action_size=agent.action_size())
target_q = None
if args_gpu >= 0:
    cuda.check_cuda_available()
    gpu_device = args_gpu
    cuda.get_device(gpu_device).use()
    xp = cuda.cupy
    q.to_gpu()

POOL_SIZE = args_pool_size
state_pool = np.zeros((POOL_SIZE, 3, train_height, train_width), dtype=np.float32)
action_pool = np.zeros((POOL_SIZE,), dtype=np.int32)
reward_pool = np.zeros((POOL_SIZE,), dtype=np.float32)
terminal_pool = np.zeros((POOL_SIZE,), dtype=np.float32)

# allocate memory
state_pool[...] = 0
action_pool[...] = 0
reward_pool[...] = 0
terminal_pool[...] = 0

frame = 0
average_reward = 0

optimizer = optimizers.AdaDelta(rho=0.95, eps=1e-06)
optimizer.setup(q)
optimizer.add_hook(chainer.optimizer.GradientClipping(0.1))
if args_input is not None:
    serializers.load_hdf5('{}.model'.format(args_input), q)
    serializers.load_hdf5('{}.state'.format(args_input), optimizer)

random_probability = args_random
random_reduction_rate = 1 - args_random_reduction
min_random_probability = min(random_probability, args_min_random)


def train():
    print "started train thread."
    max_term_size = args_max_train_term
    current_term_size = args_train_term
    term_increase_rate = 1 + args_train_term_increase
    last_clock = time.clock()
    while True:
        term_size = int(current_term_size)
        if frame < batch_size * term_size:
            continue
        batch_index = np.random.permutation(min(frame - term_size, POOL_SIZE))[:batch_size]
        train_image = Variable(xp.asarray(state_pool[batch_index]))
        y = q(train_image)
        for term in range(term_size):
            next_batch_index = (batch_index + 1) % POOL_SIZE
            train_image = Variable(xp.asarray(state_pool[next_batch_index]))
            score = q(train_image)
            best_q = cuda.to_cpu(xp.max(score.data, axis=1))
            t = Variable(xp.asarray(reward_pool[batch_index] + (1 - terminal_pool[batch_index]) * gamma * best_q))
            action_index = chainer.Variable(xp.asarray(action_pool[batch_index]))
            loss = F.mean_squared_error(F.select_item(y, action_index), t)
            y = score
            optimizer.zero_grads()
            loss.backward()
            loss.unchain_backward()
            optimizer.update()
            batch_index = next_batch_index
            print "loss", float(cuda.to_cpu(loss.data))
            clock = time.clock()
            print "train", clock - last_clock
            last_clock = clock
        current_term_size = min(current_term_size * term_increase_rate, max_term_size)
        print "current_term_size ", current_term_size

def target(agent):
    print "started target thread."
    global frame, random_probability, average_reward
    try:
        thread.start_new_thread(train, ())
        next_clock = time.clock() + interval
        save_iter = 1000
        save_count = 0
        action = None
        action_q = q.copy()
        action_q.reset_state()
        while True:
            if action is not None:
                agent.send_action(action)

            screen, rear = agent.receive_image_and_args()
            reward, terminal = agent.process(screen, rear)
            if reward is not None:
                train_image = xp.asarray(screen.resize((train_width, train_height))).astype(np.float32).transpose((2, 0, 1))
                train_image = Variable(train_image.reshape((1,) + train_image.shape) / 127.5 - 1, volatile=True)
                score = action_q(train_image, train=False)

                best = int(np.argmax(score.data))
                action = agent.randomize_action(best, random_probability)
                print action, float(score.data[0][action]), best, float(score.data[0][best]), reward
                index = frame % POOL_SIZE
                state_pool[index] = cuda.to_cpu(train_image.data)
                action_pool[index] = action
                reward_pool[index - 1] = reward
                average_reward = average_reward * 0.9999 + reward * 0.0001
                print "average reward: ", average_reward
                if terminal:
                    terminal_pool[index - 1] = 1
                    action_q = q.copy()
                    action_q.reset_state()
                else:
                    terminal_pool[index - 1] = 0
                frame += 1
                save_iter -= 1
                random_probability *= random_reduction_rate
                if random_probability < min_random_probability:
                    random_probability = min_random_probability
            else:
                action = None

            if save_iter <= 0:
                print 'save: ', save_count
                serializers.save_hdf5('{0}_{1:03d}.model'.format(args_output, save_count), q)
                serializers.save_hdf5('{0}_{1:03d}.state'.format(args_output, save_count), optimizer)
                save_iter = 10000
                save_count += 1
            current_clock = time.clock()
            wait = next_clock - current_clock
            print 'wait: ', wait
            if wait > 0:
                next_clock += interval
                time.sleep(wait)
            elif wait > -interval / 2:
                next_clock += interval
            else:
                next_clock = current_clock + interval
    except KeyboardInterrupt:
        pass

from flask import Flask
from flask import request
app = Flask(__name__)

agent = Agent()
thread.start_new_thread(target, (agent,))


@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print("image size: " + str(len(request.data)))
        jpg = 'robot_images/img' + request.args['n'] + '.jpg'
        outfile = open(jpg, 'ab')
        outfile.write(request.data)
        outfile.close()
        if request.args['last'] == 'y':
            print "sending image."
            image = PIL.Image.open(jpg)
            print "image opened."
            agent.send_image_and_args(image, request.args['rear'])
            action = agent.receive_action()
            return str(action)
        return '-'
    else:
        return '-'

if __name__ == "__main__":
    app.run()#host='192.168.1.10')
