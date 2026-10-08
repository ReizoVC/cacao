import copy
import json
from pathlib import Path
import unittest
import jsonschema
from integracion import adjust,pixel_point

class Integration(unittest.TestCase):
    def schema(self):
        root=Path(__file__).resolve().parents[1]
        tools=json.loads((root/'herramientas.json').read_text(encoding='utf-8'))['herramientas']
        ns={'HERRAMIENTAS':{h['nombre']:h for h in tools},'prompt_sistema':lambda voz=False:'original',
            'ESQUEMA_ACCION':{'type':'object','properties':{'pensamiento':{'type':'string'},'herramienta':{'type':'string','enum':['finalizar','volumen']},'argumentos':{'type':'object'},'mensaje_final':{'type':'string'}},'required':['pensamiento','herramienta','argumentos']}}
        adjust(ns)
        return ns['ESQUEMA_ACCION']
    def test_final_message_required(self):
        schema=self.schema()
        value={'pensamiento':'Respondo.','herramienta':'finalizar','argumentos':{},'mensaje_final':'Hola'}
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(value,schema)
        value.pop('mensaje_final');value['argumentos']={'mensaje':'Hola','exito':True}
        jsonschema.validate(value,schema)
        value['argumentos']['mensaje']=''
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(value,schema)
    def test_shortcut_disabled(self):
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({'pensamiento':'Ajusto.','herramienta':'volumen','argumentos':{'accion':'consultar'},'mensaje_final':'Listo'},self.schema())
    def test_coordinate_axes(self):
        self.assertEqual(pixel_point('gemma_q5',{'box_2d':[100,200,300,400]},500,1000),{'x':150,'y':200})
        self.assertEqual(pixel_point('qwen_q5',{'point_2d':[300,200]},500,1000),{'x':150,'y':200})
        with self.assertRaises(ValueError):pixel_point('gemma_q5',{'box_2d':[300,200,100,400]},500,1000)
    def test_compiled_grammar_excludes_json_controls(self):
        from llama_cpp.llama_grammar import json_schema_to_gbnf
        schema=self.schema()
        grammar=json_schema_to_gbnf(json.dumps(schema))
        self.assertIn(r'[^"\\\x7F\x00-\x1F]',grammar)
        # Escaped newlines remain valid; literal newlines must fail the same
        # strict parser used by the runner, without output cleanup.
        self.assertEqual(json.loads(r'{"mensaje":"a\nb"}')['mensaje'],'a\nb')
        with self.assertRaises(json.JSONDecodeError):json.loads('{"mensaje":"a\nb"}')

if __name__=='__main__':unittest.main()
