"""Pruebas rápidas del proyecto simplificado."""
import csv
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from biblioteca.dominio import Configuracion, ConstructorEscenario, teoria_mmc, comprobar_con_sympy
from biblioteca.simulacion import FabricaSimulador
from biblioteca.experimentos import ejecutar_experimento
from biblioteca.reportes import FachadaReportes


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.config = ConstructorEscenario().tasas(.8,1/3).experimentos(3,500,50,2026).construir()

    def test_builder(self):
        self.assertEqual(self.config.llegada,.8)
        self.assertEqual(self.config.replicas,3)

    def test_builder_fluido(self):
        cfg = ConstructorEscenario().tasas(.5,.25).limites(3,.8).construir()
        self.assertEqual((cfg.llegada,cfg.servicio,cfg.espera_maxima),(.5,.25,3))

    def test_valida_tasas(self):
        with self.assertRaises(ValueError): Configuracion(llegada=0)

    def test_valida_tiempos(self):
        with self.assertRaises(ValueError): Configuracion(calentamiento=12000)

    def test_rho_4(self):
        self.assertAlmostEqual(teoria_mmc(.8,1/3,4)['rho'],.6,places=9)

    def test_wq_3(self):
        self.assertAlmostEqual(teoria_mmc(.8,1/3,3)['Wq'],3.235955056,places=6)

    def test_lq_3_regresion(self):
        self.assertAlmostEqual(teoria_mmc(.8,1/3,3)['Lq'],2.588764045,places=6)

    def test_inestable(self):
        resultado=teoria_mmc(.8,1/3,2)
        self.assertFalse(resultado['estable'])
        self.assertTrue(math.isinf(resultado['Wq']))

    def test_strategy_determinista(self):
        import numpy as np
        rng=np.random.default_rng(1)
        self.assertEqual(FabricaSimulador.distribucion('determinista',.5).intervalo(rng),2.)

    def test_strategy_erlang(self):
        import numpy as np
        self.assertGreater(FabricaSimulador.distribucion('erlang',.5).intervalo(np.random.default_rng(1)),0)

    def test_semilla_reproducible(self):
        a=FabricaSimulador.crear(self.config,4,2026,1).ejecutar()
        b=FabricaSimulador.crear(self.config,4,2026,1).ejecutar()
        self.assertEqual((a.Wq,a.Lq,a.rho),(b.Wq,b.Lq,b.rho))

    def test_observer_rho_rango(self):
        r=FabricaSimulador.crear(self.config,4,2026,1).ejecutar()
        self.assertTrue(0 <= r.rho <= 1)

    def test_csv_serie_eventos(self):
        resultados, elegido=ejecutar_experimento(self.config,(3,4))
        with tempfile.TemporaryDirectory() as carpeta:
            ruta=Path(carpeta)
            html=FachadaReportes(ruta).generar(self.config,resultados,elegido)
            self.assertTrue(html.is_file())
            self.assertTrue((ruta/'Resultados/netlogo_serie_c4.csv').is_file())
            self.assertTrue((ruta/'Resultados/netlogo_eventos_c4.csv').is_file())
            with (ruta/'Resultados/netlogo_escenarios.csv').open(encoding='utf-8') as f:
                self.assertEqual(next(csv.reader(f))[0],'c')
            self.assertIn('REPRODUCIR',html.read_text(encoding='utf-8'))

    def test_casi_saturado_se_bloquea(self):
        cfg=Configuracion(llegada=2.9999,servicio=3.,replicas=1,horizonte=500,calentamiento=50)
        with self.assertRaisesRegex(ValueError,'saturación'):
            ejecutar_experimento(cfg,(1,))

    def test_sympy(self):
        with tempfile.TemporaryDirectory() as d:
            ruta=Path(d)/'sympy.txt'
            comprobar_con_sympy(.8,1/3,(3,4),ruta)
            self.assertIn('Wq SymPy',ruta.read_text(encoding='utf-8'))

    def test_netlogo7_xml(self):
        model=Path(__file__).resolve().parents[1]/'NetLogo/Biblioteca_MMc_NETLOGO7.nlogox'
        self.assertEqual(ET.parse(model).getroot().tag,'model')
        self.assertIn('netlogo_escenarios.csv',model.read_text(encoding='utf-8'))


if __name__=='__main__': unittest.main()
