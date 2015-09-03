# To make an emojified image given a regular image
# inspired by this news feed:
# http://news.dzwww.com/shehuixinwen/201509/t20150903_13011163.htm
import os
import sys
from PIL import Image, ImageDraw

EMOJI_SIZE = 32
emojis = []
avg_colors = []

def load_emojis():
    # load the emoji files
    script_path = os.path.dirname(os.path.realpath(__file__))
    emoji_path = os.path.join(script_path, "emoji")
    fnames = os.listdir(emoji_path)
    for fname in fnames:
        fullname = os.path.join(emoji_path, fname)
        _, ext = os.path.splitext(fname)
        # make sure it is emoji png
        if os.path.isfile(fullname) and ext.lower() == ".png":
            im = Image.open(fullname)
            rgbim = im.convert("RGBA")
            w,h = im.size
            # compute the center average
            r, g, b = 0,0,0
            cnt = 0
            for i in range(w/8, 7*w/8):
                for j in range(h/8, 7*h/8):
                    cnt += 1
                    pr, pg, pb,_ = rgbim.getpixel((i,j))
                    r += pr
                    g += pg
                    b += pb
            # put the emoji and colors into containers
            emoji_color = r/cnt, g/cnt, b/cnt
            emojis.append(rgbim)
            avg_colors.append(emoji_color)
    print "Emojis loaded ..."

# experiment with different distance functions
def distance1(c1, c2):
    r, g, b = c1
    tr, tg, tb = c2
    return abs(r-tr) + abs(g-tg) +abs(b-tb)

def distance2(c1, c2):
    # http://www.compuphase.com/cmetric.htm
    r, g, b = c1
    tr, tg, tb = c2
    return 3*(r-tr)**2 + 4*(g-tg)**2 + 2*(b-tb)**2

# find the right emoji to replace the pixel(s)
def find_emoji(color):
    min_distance = sys.maxint
    index = -1
    for i in range(len(avg_colors)):
         distance = distance2(color, avg_colors[i])
         if distance < min_distance:
             min_distance = distance
             index = i
    assert index >= 0
    #print "found emoji %d"%index
    return emojis[index]
        
def convert_image(image_path):
    try:
        img = Image.open(image_path)
    except IOError:
        print "Fail to open file %s"%image_path
        return
    img.convert("RGB")
    w, h = img.size

    # For large images, we convert pixel blocks
    # Consider 512 as the threshold
    unit = w/128 + 1
    print "Replacing %d x %d squares with emojis"%(unit, unit)
    neww, newh = w/unit, h/unit
    new_im = Image.new("RGBA", (neww*EMOJI_SIZE, newh*EMOJI_SIZE))
    # canvas = ImageDraw.Draw(new_im)
    print "Starting to draw emojis ..."
    for x in range(neww):
        for y in range(newh):
            startx, starty = unit*x, unit*y
            rr, gg, bb = 0,0,0
            for xx in range(startx, startx+unit):
                for yy in range(starty, starty+unit):
                    _r, _g, _b = img.getpixel((xx, yy))
                    rr += _r
                    gg += _g
                    bb += _b
            avg = rr/(unit*unit), gg/(unit*unit), bb/(unit*unit)
            #print avg
            emoji = find_emoji(avg)

            canvas_x, canvas_y = x*EMOJI_SIZE, y*EMOJI_SIZE
            new_im.paste(emoji, box=(canvas_x, canvas_y,
                               canvas_x+EMOJI_SIZE, canvas_y+EMOJI_SIZE), mask=emoji)
    print "Finished drawing emojified image ..."

    new_im.show()
    target_path = os.path.join(os.path.dirname(image_path), "emojified.jpg")
    new_im.save(target_path)
    print "Image saved here: %s"%target_path

def main():
    if len(sys.argv)<2:
        print "Please specify the image file to convert."
        raise SystemExit
    fname = sys.argv[1]
    load_emojis()
    convert_image(fname)

if __name__ == "__main__":
    main()
    
    
            
