"""CAPA INFRAESTRUCTURA: Facade exporta todos los resultados de un solo paso."""
from __future__ import annotations
import base64
import csv
import json
from math import inf, isfinite
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .dominio import comprobar_con_sympy, teoria_mmc


class FachadaReportes:
    """FACADE: oculta detalles de CSV, SymPy, imágenes y dashboard HTML."""
    def __init__(self, carpeta_proyecto):
        self.datos = Path(carpeta_proyecto)/'Resultados'
        self.graficas = Path(carpeta_proyecto)/'Resultados_Graficas'
        self.datos.mkdir(exist_ok=True,parents=True)
        self.graficas.mkdir(exist_ok=True,parents=True)

    def _csv(self, nombre, cabecera, filas):
        with (self.datos/nombre).open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f)
            w.writerow(cabecera)
            w.writerows(filas)

    @staticmethod
    def _normal(numero):
        return round(numero,9) if numero is not None and isfinite(numero) else ''

    def generar(self,config,resultados,recomendado):
        self._guardar_csv(config,resultados,recomendado)
        if config.es_mmc:
            comprobar_con_sympy(config.llegada,config.servicio,[e.c for e in resultados],
                                  self.datos/'analisis_simbolico_sympy.txt')
        else:
            (self.datos/'analisis_simbolico_sympy.txt').write_text(
                'Las ecuaciones M/M/c son solo válidas si llegada y servicio son exponenciales.\n',encoding='utf-8')
        imagenes = self._graficar(config,resultados)
        html = self._html(config,resultados,recomendado,imagenes)
        return html

    def _guardar_csv(self, cfg, resultados,recomendado):
        # Evitar que NetLogo cargue CSV antiguos si se reduce el conjunto de escenarios.
        for antiguo in list(self.datos.glob('netlogo_serie_c*.csv')) + list(self.datos.glob('netlogo_eventos_c*.csv')):
            antiguo.unlink()
        self._csv('tabla_III_teoria.csv', ['c','rho','P0','Lq','Wq','P_espera','estable'],[
            [e.c, self._normal(e.teoria['rho']), self._normal(e.teoria['P0']),
             self._normal(e.teoria['Lq']),self._normal(e.teoria['Wq']),
             self._normal(e.teoria['P_espera']), 'si' if e.teoria['estable'] else 'no']
            if e.teoria else [e.c,'','','','','','no M/M/c'] for e in resultados])
        self._csv('tabla_IV_comparacion.csv',
                  ['c','Wq_teorico','Wq_simulado','Wq_IC95_inf','Wq_IC95_sup',
                   'Lq_teorico','Lq_simulado','Lq_IC95_inf','Lq_IC95_sup','rho_teorico','rho_simulado'],[
            [e.c,self._normal(e.teoria['Wq'] if e.teoria else None),self._normal(e.Wq['media']),
             self._normal(e.Wq['inferior']),self._normal(e.Wq['superior']),
             self._normal(e.teoria['Lq'] if e.teoria else None),self._normal(e.Lq['media']),
             self._normal(e.Lq['inferior']),self._normal(e.Lq['superior']),
             self._normal(e.teoria['rho'] if e.teoria else None),self._normal(e.rho['media'])]
            for e in resultados])
        self._csv('tabla_V_decision.csv', ['c','Wq_simulado','rho_simulado','cumple'],[
            [e.c,e.Wq['media'],e.rho['media'],'si' if e.cumple else 'no'] for e in resultados])
        if cfg.es_mmc:
            self._csv('tabla_VI_sensibilidad.csv', ['lambda','c','Wq_teorico','rho','estable'],[
                [lam,e.c,self._normal(theory['Wq']),theory['rho'],'si' if theory['estable'] else 'no']
                for lam in (.6,.8,1.) for e in resultados
                for theory in [teoria_mmc(lam,cfg.servicio,e.c)]])
        self._csv('replicas_detalladas.csv',
                  ['c','replica','semilla','Wq','Lq','rho','prob_espera','usuarios_medidos','llegadas','pico_cola'],
                  [[r.c,r.replica,r.semilla,r.Wq,r.Lq,r.rho,r.prob_espera,r.usuarios_medidos,r.llegadas,r.pico_cola]
                   for e in resultados for r in e.replicas])
        self._csv('netlogo_escenarios.csv',
                  ['c','Wq_teorico','Wq_simulado','Lq_teorico','Lq_simulado','rho','estable','cumple'],[
            [e.c,self._normal(e.teoria['Wq'] if e.teoria else None),self._normal(e.Wq['media']),
             self._normal(e.teoria['Lq'] if e.teoria else None),self._normal(e.Lq['media']),
             e.teoria['rho'] if e.teoria else e.rho['media'],
             'si' if e.teoria and e.teoria['estable'] else 'no' if e.teoria else 'no M/M/c',
             'si' if e.cumple else 'no'] for e in resultados])
        for e in resultados:
            if e.c < 3: continue
            self._csv(f'netlogo_serie_c{e.c}.csv',
                      ['tiempo_min','cola','ocupados','puestos'],e.replicas[0].serie)
            self._csv(f'netlogo_eventos_c{e.c}.csv',
                      ['tiempo_min','evento','usuario_id','puesto'],e.replicas[0].eventos)
        (self.datos/'parametros_ejecucion.json').write_text(json.dumps({
            'lambda':cfg.llegada,'mu':cfg.servicio,'puestos':[e.c for e in resultados],
            'replicas':cfg.replicas,'horizonte':cfg.horizonte,'calentamiento':cfg.calentamiento,
            'semilla':cfg.semilla,'espera_maxima':cfg.espera_maxima,
            'utilizacion_maxima':cfg.utilizacion_maxima,'recomendado':recomendado,
            'dist_llegada':cfg.dist_llegada,'dist_servicio':cfg.dist_servicio,
        },indent=2,ensure_ascii=False),encoding='utf-8')

    def _graficar(self, cfg, resultados):
        filas = [e for e in resultados if e.teoria and e.teoria['estable']]
        hechos = []
        for clave, titulo, umbral, nombre in [
            ('Wq','Espera media en cola (min)',cfg.espera_maxima,'fig_espera_python.png'),
            ('Lq','Longitud media de cola (usuarios)',None,'fig_cola_python.png'),
            ('rho','Utilización de puestos',cfg.utilizacion_maxima,'fig_utilizacion_python.png')]:
            fig,ax=plt.subplots(figsize=(7,3.7))
            if filas:
                x=[e.c for e in filas]
                teor=[e.teoria[clave] for e in filas]
                sim=[e.Wq['media'] if clave=='Wq' else e.Lq['media'] if clave=='Lq' else e.rho['media'] for e in filas]
                ax.plot(x,teor,'-o',label='Teórico')
                ax.plot(x,sim,'--s',label='Simulado')
                ax.set_xticks(x)
            if umbral is not None:
                ax.axhline(umbral,ls=':',label=f'Umbral: {umbral:g}')
            ax.set_xlabel('Número de puestos (c)')
            ax.set_ylabel(titulo)
            ax.grid(alpha=.25)
            ax.legend()
            fig.tight_layout()
            fig.savefig(self.graficas/nombre,dpi=140)
            plt.close(fig)
            hechos.append(self.graficas/nombre)
        return hechos

    def _html(self,cfg,resultados,recomendado,imagenes):
        # Dashboard autocontenido; funciona sin internet ni servidor.
        datos = []
        for e in resultados:
            th=e.teoria
            datos.append({'c':e.c,'estable': bool(th['estable']) if th else False,
                          'rho':e.rho['media'],'wq':e.Wq['media'],'wq_teorico':th['Wq'] if th and th['estable'] else None,
                          'ic':[e.Wq['inferior'],e.Wq['superior']], 'cumple':e.cumple,
                          'serie':e.replicas[0].serie})
        imgs = [base64.b64encode(p.read_bytes()).decode('ascii') for p in imagenes]
        resumen = json.dumps(datos,ensure_ascii=False,allow_nan=False)
        cards = ''.join(f'<img alt="Gráfica {i}" src="data:image/png;base64,{src}">' for i,src in enumerate(imgs,1))
        filas=''.join(f'<tr><td>{e.c}</td><td>{e.teoria["Wq"]:.3f}'
                     f' min</td><td>{e.Wq["media"]:.3f} min</td><td>[{e.Wq["inferior"]:.3f}; {e.Wq["superior"]:.3f}]</td>'
                     f'<td>{e.rho["media"]:.3f}</td><td>{"✅ Sí" if e.cumple else "❌ No"}</td></tr>'
                     if e.teoria and e.teoria['estable'] else
                     f'<tr><td>{e.c}</td><td>Inestable</td><td>No estacionario</td><td>—</td><td>{e.rho["media"]:.3f}</td><td>❌ No</td></tr>'
                     for e in resultados)
        html = r'''<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Biblioteca · Simulación M/M/c</title>
<style>body{font-family:system-ui,Arial;background:#101a2b;color:#edf3ff;margin:0}header{background:#16263f;padding:30px 5vw}h1{margin:0;font-size:2rem}.sub{opacity:.82}main{max-width:1120px;margin:auto;padding:24px 18px}.panel{background:#1c2c46;padding:20px;border-radius:14px;margin:20px 0}h2{margin:0 0 15px}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #40516a;text-align:left}th{color:#acd6ff}.kpi{font-size:2.2rem;font-weight:bold;color:#72e8b6}.charts{display:flex;flex-wrap:wrap;gap:15px}.charts img{width: min(100%,510px);background:white;border-radius:8px}button,select{background:#3988eb;color:white;border:0;padding:10px 16px;border-radius:7px;font-weight:700;cursor:pointer}select{color:white}canvas{background:#0a1524;border:1px solid #3a5575;width:100%;max-width:880px;border-radius:12px}.small{opacity:.75;font-size:.93rem}.warn{background:#52441a;padding:12px;border-radius:8px;color:#fff1ba}</style></head>
<body><header><h1>Biblioteca Universitaria · Simulación M/M/c</h1><div class="sub">Python · SymPy · NetLogo 7 · Arquitectura por capas · 5 patrones</div></header><main>
<section class="panel"><h2>Resultado principal</h2><div class="kpi" id="recommend"></div><p>Con tasas supuestas λ=__LAM__ usuarios/min y μ=__MU__ usuarios/min por puesto; espera máxima __WAIT__ min y utilización máxima __UTIL__.</p><p class="warn">Estos resultados describen escenarios de prueba. No son mediciones reales de una biblioteca.</p></section>
<section class="panel"><h2>Comparación de escenarios</h2><div style="overflow:auto"><table><thead><tr><th>Puestos</th><th>Wq teórica</th><th>Wq simulada</th><th>IC 95 % Wq</th><th>ρ simulada</th><th>¿Cumple?</th></tr></thead><tbody>__ROWS__</tbody></table></div></section>
<section class="panel"><h2>Gráficas del experimento</h2><div class="charts">__CHARTS__</div></section>
<section class="panel"><h2>Reproducción de estados registrados (primera réplica)</h2><p class="small">La reproducción utiliza una muestra temporal del CSV de Python. No crea llegadas nuevas ni representa trayectorias individuales medidas.</p><label for="select">Escenario: </label><select id="select"></select> <button onclick="step()">PASO</button> <button onclick="toggle()" id="play">REPRODUCIR</button> <button onclick="reset()">REINICIAR</button><p id="estado"></p><canvas id="canvas" width="880" height="280"></canvas></section>
<footer class="small">Generado localmente desde Python. NetLogo carga los CSV de Resultados/. Si se modifican λ, μ o las réplicas, se debe ejecutar de nuevo Python y actualizar el informe.</footer></main>
<script>const scenarios=__DATA__;let selected,idx=0,timer=null;const selector=document.getElementById('select'),canvas=document.getElementById('canvas'),ctx=canvas.getContext('2d');document.getElementById('recommend').textContent=__RECOMMEND__;
scenarios.filter(s=>s.serie.length).forEach(s=>{let opt=document.createElement('option');opt.value=s.c;opt.textContent=s.c+' puestos';selector.appendChild(opt)});selector.value=scenarios.find(s=>s.c===4&&s.serie.length)?4:(scenarios.find(s=>s.serie.length)||{}).c;selector.onchange=()=>reset();function current(){return scenarios.find(s=>''+s.c===selector.value)}function render(){const s=current();if(!s)return;const row=s.serie[Math.min(idx,s.serie.length-1)];if(!row)return;const [t,q,b,c]=row;document.getElementById('estado').textContent=`Minuto ${t} · En cola: ${q} · Puestos ocupados: ${b} de ${c}`;ctx.clearRect(0,0,880,280);ctx.font='bold 19px Arial';ctx.fillStyle='#f4f7fc';ctx.fillText('ENTRADA',35,37);ctx.fillText('FILA',260,37);ctx.fillText('ATENCIÓN',540,37);for(let j=0;j<Math.min(q,12);j++){ctx.fillStyle='#ffab40';ctx.beginPath();ctx.arc(220+(j%4)*48,90+Math.floor(j/4)*44,13,0,Math.PI*2);ctx.fill()}for(let j=0;j<c;j++){let x=535+(j%4)*72,y=85+Math.floor(j/4)*70;ctx.fillStyle=j<b?'#43c583':'#4e89d9';ctx.fillRect(x,y,45,36)}ctx.fillStyle='#bacde3';ctx.font='14px Arial';ctx.fillText('Naranja: en cola  ·  Verde: ocupado  ·  Azul: libre',35,247)}function step(){let s=current();if(!s||!s.serie.length)return;idx=Math.min(idx+1,s.serie.length-1);render();if(idx===s.serie.length-1)stop()}function stop(){if(timer)clearInterval(timer);timer=null;document.getElementById('play').textContent='REPRODUCIR'}function toggle(){if(timer){stop();return}timer=setInterval(step,120);document.getElementById('play').textContent='PAUSAR'}function reset(){stop();idx=0;render()}reset();</script></body></html>'''
        html=(html.replace('__ROWS__',filas).replace('__CHARTS__',cards).replace('__DATA__',resumen)
              .replace('__LAM__',f'{cfg.llegada:g}').replace('__MU__',f'{cfg.servicio:.6f}')
              .replace('__WAIT__',f'{cfg.espera_maxima:g}').replace('__UTIL__',f'{cfg.utilizacion_maxima:g}')
              .replace('__RECOMMEND__',json.dumps(f'{recomendado} puestos recomendados' if recomendado else 'Sin escenario que cumpla')))
        destino=self.datos/'dashboard.html'
        destino.write_text(html,encoding='utf-8')
        return destino
