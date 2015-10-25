# My clone of Minecraft using python and Panda3D 
from panda3d.core import GeomVertexFormat, GeomVertexData
from panda3d.core import Geom, GeomTriangles, GeomVertexWriter
from panda3d.core import Texture, GeomNode
from direct.showbase.ShowBase import ShowBase
import random, math

# helper functions to draw a primitive cube
def makeSquare(x1, y1, z1, x2, y2, z2):
    format = GeomVertexFormat.getV3n3cpt2()
    vdata = GeomVertexData('square', format, Geom.UHDynamic)

    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    # color = GeomVertexWriter(vdata, 'color')
    texcoord = GeomVertexWriter(vdata, 'texcoord')

    # make sure we draw the sqaure in the right plane
    if x1 != x2:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y1, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y2, z2)

        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z2 - 1))
        normal.addData3(normalized(2 * x1 - 1, 2 * y2 - 1, 2 * z2 - 1))

    else:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y2, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y1, z2)

        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z2 - 1))
        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z2 - 1))

    # adding different colors to the vertex for visibility
    # color.addData4f(1.0, 0.0, 0.0, 1.0)
    # color.addData4f(0.0, 1.0, 0.0, 1.0)
    # color.addData4f(0.0, 0.0, 1.0, 1.0)
    # color.addData4f(1.0, 0.0, 1.0, 1.0)

    texcoord.addData2f(0.0, 1.0)
    texcoord.addData2f(0.0, 0.0)
    texcoord.addData2f(1.0, 0.0)
    texcoord.addData2f(1.0, 1.0)

    # Quads aren't directly supported by the Geom interface
    # you might be interested in the CardMaker class if you are
    # interested in rectangle though
    tris = GeomTriangles(Geom.UHDynamic)
    tris.addVertices(0, 1, 3)
    tris.addVertices(1, 2, 3)

    square = Geom(vdata)
    square.addPrimitive(tris)
    return square

def makeCube():
   	square0 = makeSquare(-1, -1, -1, 1, -1, 1)
	square1 = makeSquare(-1, 1, -1, 1, 1, 1)
	square2 = makeSquare(-1, 1, 1, 1, -1, 1)
	square3 = makeSquare(-1, 1, -1, 1, -1, -1)
	square4 = makeSquare(-1, -1, -1, -1, 1, 1)
	square5 = makeSquare(1, -1, -1, 1, 1, 1)
	snode = GeomNode('square')
	snode.addGeom(square0)
	snode.addGeom(square1)
	snode.addGeom(square2)
	snode.addGeom(square3)
	snode.addGeom(square4)
	snode.addGeom(square5)
	return snode
		
WORLD_SIZE = 128
SECTOR_SIZE = 8
SECTOR_RADIUS = 3
NEIGHBOURS = [
    ( 0, 1, 0),
    ( 0,-1, 0),
    (-1, 0, 0),
    ( 1, 0, 0),
    ( 0, 0, 1),
    ( 0, 0,-1),
]
MOVE_SPEED = 0.5
ROTATE_SPEED = 0.15
GRAVITY = 0.2

def position_to_sector(pos):
	x, y, z = pos
	xx, yy = int(round(x))/SECTOR_SIZE, int(round(y))/SECTOR_SIZE
	return xx, yy

class Game(ShowBase):
	textures = ["STONE", "BRICK", "SAND", "GRASS"]
	def __init__(self):
		self.world = {}
		self.block_nodes = {}
		self.sectors = set()
		self.sector_blocks = {}
		self.position = (0,0,1)
		self.lookat = [0, 0] # horizontal and vertial camera direction
		
		self.flying = False
		self.vspeed = 0
		self.move_direction= [0,0]
		# mouse positions
		self.mx = None
		self.my = None

		self.generate_initial_world()
		self.refresh_sectors()
		self.update_camera()
		self.register_handlers()
		self.add_tasks()

	def register_handlers(self):
		self.accept("w", self.move_forward)
		self.accept("s", self.move_backward)
		self.accept("a", self.move_left)
		self.accept("d", self.move_right)
		self.accept("w-up", self.stop_move_forward)
		self.accept("s-up", self.stop_move_backward)
		self.accept("a-up", self.stop_move_left)
		self.accept("d-up", self.stop_move_right)
		self.accept("mouse1", self.erase_block)
		self.accept("mouse2", self.create_block)
		self.accept("tab", self.toggle_flying)
		self.accept(" ", self.jump)

	def move_forward(self):
		self.move_direction[0]+=1

	def move_backward(self):
		self.move_direction[0]-=1

	def move_left(self):
		self.move_direction[1]-=1

	def move_right(self):
		self.move_direction[1]+=1

	def stop_move_forward(self):
		self.move_direction[0]-=1

	def stop_move_backward(self):
		self.move_direction[0]+=1

	def stop_move_left(self):
		self.move_direction[1]+=1

	def stop_move_right(self):
		self.move_direction[1]-=1

	def erase_block(self):
		# find the block looked at
		# remove the block from world and sector_blocks
		# remove the node for the block
		pass

	def toggle_flying(self):
		self.flying = not self.flying

	def jump(self):
		if self.vspeed == 0:
			self.vspeed = self.MOVE_SPEED

	def add_tasks(self):
		self.taskMgr.add(self.move_task, "move_task")
		self.taskMgr.add(self.mouse_task, "mouse_task")

	def detect_collision(self, pos):
		return pos

	def move_task(self):
		# first check if moving in any direction
		if any(self.move_direction):
			radian = math.atan2(self.move_direction[1], self.move_direction[0])
			degree = math.degrees(radian)
			move_z = math.radians(self.lookat[1])
			move_x = math.radians(self.lookat[0]+degree)

			if self.flying:
				if self.move_direction[1]:
					vspeed = 0.0
					hspeed = MOVE_SPEED
				else:
					vspeed = MOVE_SPEED * math.sin(move_z)
					hspeed = MOVE_SPEED * math.cos(move_z)
				if self.move_direction[0] <0:
					hspeed = -hspeed
			else:
				hspeed = MOVE_SPEED
				vspeed = 0
			x_speed = hspeed * math.cos(move_x)
			y_speed = hspeed * math.sin(move_x)
			newpos = self.position[0]+x_speed, self.position[1]+y_speed, self.position[2]+hspeed
			self.position = self.detect_collision(newpos)
			# TODO: if cross sector, render sectors
		# second check if dropping when not flying
		if not self.flying:
			newpos = self.position[0], self.position[1], self.position[2]+self.vspeed
			self.position = self.detect_collision(newpos)
			self.vspeed -= GRAVITY

	def mouse_task(self):
		mw = self.mouseWatcherNode
		if mw.hasMouse():
			mpos = mw.getMouse()  # get the mouse position
			if self.mx is None or self.my is None:
				self.mx = mpos.getX()
				self.my = mpos.getY()
			else:
				dx = mpos.getX() - self.mx
				dy = mpos.getY() - self.my
				self.lookat[0] += ROTATE_SPEED*dx
				self.lookat[1] += ROTATE_SPEED*dy
				if self.lookat[1] > 90.0:
					self.lookat[1] = 90
				elif self.lookat[1]<-90.0:
					self.lookat[1] = -90
				self.update_camera()

	def add_block(self, pos, tex_idx):
		self.world[pos] = tex_idx
		sector = position_to_sector(pos)
		self.sector_blocks.setdefault(sector, []).append(pos)

	def generate_initial_world(self):
		for x in range(-WORLD_SIZE, WORLD_SIZE+1):
			for y in range(-WORLD_SIZE, WORLD_SIZE+1):
				self.add_block((x, y, -2), 0) # a layer of stones
				self.add_block((x, y, -1), 3) # a layer of grass

		for _ in range(20):
			# generate random hills
			hillx = random.randint(-WORLD_SIZE, WORLD_SIZE)
			hilly = random.randint(-WORLD_SIZE, WORLD_SIZE)
			size = random.randint(2, 6)
			height = random.randint(3, 8)
			texture = random.randint(0,4)
			for i in range(height):
				for m in range(hillx-size, hillx+size):
					for n in range(hilly-size, hilly+size):
						self.add_block((m,n,i), texture)
				size -= 1
				if size <= 0: break

	def update_camera(self):
		x, y, z = self.position
		self.camera.setPos(x, y, z)
		self.camera.setHpr(*self.lookat)

	def show_block(self, x, y, z, texture):
		cube = makeCube()
		node = self.render.attachNewNode(cube)                     
		node.setPos(x, y, z)
		node.setTexture(texture)
		return node

	def hide_block(self, pos):
		if pos in self.block_nodes:
			self.block_nodes[pos].removeNode()
			del self.block_nodes[pos]

	def exposed(self, pos):
		x, y, z = pos
		for dx, dy, dz in NEIGHBOURS:
			if (x+dx, y+dy, z+dz) not in self.world:
				return True
		return False

	def refresh_sectors(self):
		sx, sy = position_to_sector(self.position)
		new_sectors = set()
		for i in range(sx-SECTOR_RADIUS, sx+SECTOR_RADIUS+1):
			for j in range(sy-SECTOR_RADIUS, sy+SECTOR_RADIUS+1):
				if (i-sx)**2 + (j-sy)**2 > SECTOR_RADIUS**2: continue
				new_sectors.add((i, j))
		added = new_sectors - self.sectors
		deleted = self.sectors - new_sectors
		for sector in added:
			blocks = self.sector_blocks[sector]
			for block in blocks:
				if not self.exposed(block): continue
				x, y, z = block
				tex_idx = self.world[block]
				texture = self.get_texture(tex_idx)
				node = self.show_block(x, y, z, texture)
				self.block_nodes[block] = node
		for sector in deleted:
			blocks = self.sector_blocks[sector]
			for block in blocks:
				self.hide_block(block)
		self.sectors = new_sectors

	def get_texture(self, idx):
		pass

	def load_textures(self):
		pass

game = Game()
game.run()

