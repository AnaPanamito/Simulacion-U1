"""CAPA PRESENTACIÓN: ejecución desde consola y parámetros del experimento."""
from __future__ import annotations
import argparse
import webbrowser
from pathlib import Path
from biblioteca.dominio import ConstructorEscenario
from biblioteca.experimentos import ejecutar_experimento
from biblioteca.reportes import FachadaReportes


def main():
    parser = argparse.ArgumentParser(description='Biblioteca Universitaria: teoría de colas M/M/c')
    parser.add_argument('--lambda-rate',type=float,default=.8,help='Llegadas por minuto')
    parser.add_argument('--mu-rate',type=float,default=1/3,help='Atenciones/minuto por puesto')
    parser.add_argument('--puestos',default='2,3,4,5,6',help='Lista de puestos, ej. 3,4,5')
    parser.add_argument('--replicas',type=int,default=30)
    parser.add_argument('--horizonte',type=float,default=12000)
    parser.add_argument('--calentamiento',type=float,default=1200)
    parser.add_argument('--semilla',type=int,default=2026)
    parser.add_argument('--dist-llegada',choices=['exponencial','determinista','erlang'],default='exponencial')
    parser.add_argument('--dist-servicio',choices=['exponencial','determinista','erlang'],default='exponencial')
    parser.add_argument('--rapido',action='store_true',help='Modo demostración: 3 réplicas, 1000 minutos')
    parser.add_argument('--abrir-html',action='store_true')
    args = parser.parse_args()
    try:
        puestos = tuple(int(s.strip()) for s in args.puestos.split(',') if s.strip())
        replicas, horizonte, calentamiento = (3,1000,100) if args.rapido else (args.replicas,args.horizonte,args.calentamiento)
        cfg = (ConstructorEscenario().tasas(args.lambda_rate,args.mu_rate)
               .experimentos(replicas,horizonte,calentamiento,args.semilla)
               .distribuciones(args.dist_llegada,args.dist_servicio).construir())
        resultados, recomendado = ejecutar_experimento(cfg, puestos)
        print('\nBIBLIOTECA UNIVERSITARIA | MODELO M/M/c')
        print(f'lambda={cfg.llegada:g}, mu={cfg.servicio:g}, réplicas={cfg.replicas}, horizonte={cfg.horizonte:g}, calentamiento={cfg.calentamiento:g}')
        print(f'{"c":>3} {"rho teoría":>12} {"Wq teoría":>12} {"Wq simulada":>13} {"IC 95%":>19} {"Cumple":>8}')
        for e in resultados:
            th = e.teoria
            tasa = f'{th["rho"]:.3f}' if th else 'N/A'
            esperado = f'{th["Wq"]:.3f}' if th and th['estable'] else 'Inestable' if th else 'N/A'
            print(f'{e.c:>3} {tasa:>12} {esperado:>12} {e.Wq["media"]:>13.3f} '
                  f'[{e.Wq["inferior"]:>6.3f};{e.Wq["superior"]:>6.3f}] {"SI" if e.cumple else "NO":>8}')
        print('\nRECOMENDACION:',f'{recomendado} puestos' if recomendado is not None else 'ningún escenario cumple')
        carpeta = Path(__file__).resolve().parent
        html = FachadaReportes(carpeta).generar(cfg,resultados,recomendado)
        print('Archivos creados en Resultados/ y Resultados_Graficas/')
        print('HTML:',html)
        if args.abrir_html:
            webbrowser.open(html.as_uri())
    except (ValueError,ArithmeticError) as exc:
        parser.exit(status=2,message=f'ERROR: {exc}\n')

if __name__=='__main__':
    main()
