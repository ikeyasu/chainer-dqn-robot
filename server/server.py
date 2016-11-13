from flask import Flask
from flask import request
app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
  if request.method == 'POST':
    #print(request.data)
    print(request.args['n'])
    outfile = open('img' + request.args['n'] + '.jpg', 'ab')
    outfile.write(request.data)
    outfile.close()
    return '{"status":200}'
  else:
    return '{"status":200}'

if __name__ == "__main__":
  app.run()
