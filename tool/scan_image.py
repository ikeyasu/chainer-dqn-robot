#!/usr/bin/python
from sys import argv
import zbar
#import Image
import PIL.Image

if len(argv) < 2: exit(1)

# create a reader
scanner = zbar.ImageScanner()

# configure the reader
scanner.parse_config('enable')

print argv[1],
# obtain image data
try:
  pil = PIL.Image.open(argv[1]).convert('L')
  width, height = pil.size
except:
  print ' bad image.',

raw = pil.tobytes()

# wrap image data
image = zbar.Image(width, height, 'Y800', raw)

# scan the image for barcodes
scanner.scan(image)

# extract results
print len(image.symbols), '\n'
for symbol in image:
    # do something useful with results
    print 'decoded', symbol.type, 'symbol', '"%s"' % symbol.data
    print [method for method in dir(symbol)]
    print symbol.location

# clean up
del(image)
