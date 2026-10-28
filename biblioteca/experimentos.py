"""CAPA APLICACIÓN: 30 réplicas, IC del 95 %, decisión y sensibilidad."""
from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean, stdev
from scipy.stats import t
from .dominio import teoria_mmc
from .simulacion import FabricaSimulador


@dataclass
class Escenario:
    c: int
    teoria: dict | None
    replicas: list
    Wq: dict
    Lq: dict
    rho: dict
    prob_espera: dict
    cumple: bool


def intervalo_95(numeros):
    media = mean(numeros)
    radio = t.ppf(.975,len(numeros)-1)*stdev(numeros)/sqrt(len(numeros)) if len(numeros)>1 else 0
    return {'media':media,'inferior':media-radio,'superior':media+radio}


def ejecutar_experimento(config, puestos=(2,3,4,5,6)):
    resultados = []
    for c in sorted(set(puestos)):
        if c < 1: raise ValueError('Puestos debe ser >= 1')
        uso = config.llegada/(c*config.servicio)
        if .98 <= uso < 1:
            raise ValueError(f'Escenario cercano a saturación: c={c}, rho={uso:.6f}. Umbral 98 %.')
        if not isfinite(uso): raise ValueError('Valor inválido de utilización')
        teoria = teoria_mmc(config.llegada,config.servicio,c) if config.es_mmc else None
        replicas = [FabricaSimulador.crear(config,c,config.semilla+i,i+1).ejecutar()
                    for i in range(config.replicas)]
        Wq = intervalo_95([r.Wq for r in replicas])
        Lq = intervalo_95([r.Lq for r in replicas])
        rho = intervalo_95([r.rho for r in replicas])
        prob = intervalo_95([r.prob_espera for r in replicas])
        cumple = Wq['media'] <= config.espera_maxima and rho['media'] <= config.utilizacion_maxima
        if teoria is not None:
            cumple = cumple and teoria['estable'] and teoria['Wq'] <= config.espera_maxima and teoria['rho'] <= config.utilizacion_maxima
        resultados.append(Escenario(c,teoria,replicas,Wq,Lq,rho,prob,cumple))
    recomendados = [e.c for e in resultados if e.cumple]
    return resultados, min(recomendados) if recomendados else None
