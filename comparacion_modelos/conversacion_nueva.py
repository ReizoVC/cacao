"""Repite solo conversación reutilizando el ejecutor congelado de la ronda 2.

El AST en memoria omite el bucle de las 195 tareas y exige cero casos de tarea
para completar la tanda. No cambia prompt, gramática, preguntas ni inferencia.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SOURCE=HERE/'ejecutar.py'
frozen=json.loads((HERE/'ronda2_congelado.json').read_text(encoding='utf-8'))
for name,digest in frozen.items():
    path=ROOT/name if name=='pruebas.json' else HERE/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name

class ConversationOnly(ast.NodeTransformer):
    loops=0
    conditions=0
    def visit_For(self,node):
        if isinstance(node.target,ast.Name) and node.target.id=='seed' and ast.unparse(node.iter)=='(11, 22, 33)':
            self.loops+=1
            return ast.copy_location(ast.Pass(),node)
        return self.generic_visit(node)
    def visit_Compare(self,node):
        if ast.unparse(node)=="len(report['cases']) == 195":
            self.conditions+=1
            node.comparators[0]=ast.Constant(value=0)
        return self.generic_visit(node)

tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
rewrite=ConversationOnly()
tree=ast.fix_missing_locations(rewrite.visit(tree))
assert (rewrite.loops,rewrite.conditions)==(1,1),'El ejecutor cambió: revisar adaptación'
namespace={'__file__':str(SOURCE),'__name__':'conversation_harness'}
exec(compile(tree,str(SOURCE),'exec'),namespace)
namespace['OUT']=HERE/'datos/conversacion_nueva'
namespace['main']()
