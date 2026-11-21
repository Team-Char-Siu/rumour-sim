"""Agent geometry and rendering checks without a graphics context."""
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

class AgentVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse((Path(__file__).resolve().parents[1]/'viewer_friendships.py').read_text())
    def test_pointed_geometry_preserves_area(self):
        node = next(n for n in self.tree.body if isinstance(n,ast.FunctionDef) and n.name == 'diamondPoints')
        ns = {}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'diamond','exec'),ns)
        points = ns['diamondPoints'](100,200,4)
        self.assertEqual(points,[(100,206),(103,200),(100,194),(97,200)])
        area = abs(sum(points[i][0]*points[(i+1)%4][1]-points[(i+1)%4][0]*points[i][1] for i in range(4)))/2
        self.assertEqual(area,2.25*4**2)
    def test_modest_size_increase_unchanged(self):
        sizes = {}
        for node in ast.walk(self.tree):
            if isinstance(node,ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target,ast.Attribute) and target.attr in ('DOT_IDLE','DOT_ACTIVE','DOT_HOP'):
                    sizes[target.attr] = ast.literal_eval(node.value)
        self.assertEqual(sizes,dict(DOT_IDLE=3.25,DOT_ACTIVE=5.75,DOT_HOP=4.75))
    def test_filled_diamond_and_outer_ring(self):
        class Base:
            def on_draw(self):
                pass
        original = next(n for n in self.tree.body if isinstance(n,ast.ClassDef))
        method = next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name == 'on_draw')
        cls = ast.ClassDef(name='Window',bases=[ast.Name(id='Base',ctx=ast.Load())],keywords=[],body=[method],decorator_list=[])
        tree = ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[]))
        arcade = Mock()
        base = SimpleNamespace(DIM=(120,130,155),DOT_HOP=4.75,DOT_ACTIVE=5.75,DOT_IDLE=3.25,STATE_COL=[None,(255,77,77)],SUBJECT_COL=(255,105,180))
        ns = dict(Base=Base,arcade=arcade,base=base,SPREADER=1,CORRECTOR=2,NO_GROUP=-1,math=math,
                  diamondPoints=lambda x,y,r:[(x,y+r*1.5),(x+r*.75,y),(x,y-r*1.5),(x-r*.75,y)],
                  showsAvoidance=lambda a:a.avoiding,AVOID_RING_GAP=4.5,AVOID_RING_COL=(255,95,95),AVOID_RING_WIDTH=1.4,
                  transmissionStats=lambda agents:dict(friends=0,lostFriends=0,silentBelievers=0))
        exec(compile(tree,'draw','exec'),ns)
        w = ns['Window']()
        w.agents=[SimpleNamespace(state=0,group=-1,generation=-1,isFriend=False,wasFriend=False,avoiding=True)]
        w.genMode=w.spreadMode=False
        w.told=[0]
        w.shown=[(10,20)]
        w.dots=[SimpleNamespace(color=(210,220,235,0))]
        w.toScreen=lambda p:p
        w.label=Mock()
        w.on_draw()
        arcade.draw_polygon_filled.assert_called_once()
        self.assertEqual(arcade.draw_circle_outline.call_args.args[2],3.25*1.5+4.5)
