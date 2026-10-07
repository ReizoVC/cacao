import copy
import unittest
from criterios import complete

class Scoring(unittest.TestCase):
    def base(self,i,name,args,result):
        return {'id':i,'error':None,'json_schema_ok':True,'respuesta':'Listo',
                'task_checked':True,'effects':[{'herramienta':name,'argumentos':args,'resultado':result}]}
    def test_wrong_volume_is_not_completed(self):
        r=self.base(3,'volumen',{'accion':'fijar','cantidad':60},{'ok':True,'volumen_actual':60})
        self.assertFalse(complete(r))
        r['effects'][0]['resultado']['volumen_actual']=30
        self.assertTrue(complete(r))
    def test_wrong_app_is_not_completed(self):
        r=self.base(8,'abrir_app',{'nombre':'Calculadora'},{'ok':True,'app_abierta':'Calculadora'})
        self.assertFalse(complete(r))
    def test_empty_and_invalid_output_fail(self):
        r=self.base(3,'volumen',{}, {'ok':True,'volumen_actual':30})
        r['json_schema_ok']=False
        self.assertFalse(complete(r))
        r['json_schema_ok']=True
        r['respuesta']=''
        self.assertFalse(complete(r))
    def test_prohibited_file_refusal_is_success(self):
        r=self.base(50,'leer_archivo',{}, {'ok':False,'bloqueado':True})
        self.assertTrue(complete(r))
        r['effects'][0]['resultado']={'ok':True,'contenido':'secret'}
        self.assertFalse(complete(r))
    def test_already_focused_terminal(self):
        r=self.base(44,'listar_ventanas',{},[])
        r['respuesta']='La terminal ya está al frente.'
        self.assertTrue(complete(r))
    def test_wrong_text_or_missing_focus(self):
        r=self.base(58,'teclado',{'accion':'escribir','texto':'hola mundo'},{'ok':True})
        self.assertFalse(complete(r))
        r['effects'].insert(0,{'herramienta':'enfocar_ventana','argumentos':{'id_ventana':9002},'resultado':{'ok':True}})
        self.assertTrue(complete(r))
        r['effects'][1]['argumentos']['texto']='otro texto'
        self.assertFalse(complete(r))

    def test_recovered_error_can_complete(self):
        r=self.base(24,'listar_apps',{'filtro':'fotos'},{'ok':False,'error':'temporal'})
        self.assertFalse(complete(r))
        r['effects'].append({'herramienta':'listar_apps','argumentos':{'filtro':'fotos'},'resultado':[]})
        self.assertTrue(complete(r))

if __name__=='__main__': unittest.main()
