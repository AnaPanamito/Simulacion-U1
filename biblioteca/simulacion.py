"""CAPA INFRAESTRUCTURA: Strategy, Factory, Observer y eventos discretos FIFO.

El programa NO espera en tiempo real; avanza al próximo evento de llegada/salida.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from heapq import heappush, heappop
import numpy as np


# STRATEGY: cómo se genera cada intervalo de tiempo
class Distribucion(ABC):
    @abstractmethod
    def intervalo(self, rng): ...


class Exponencial(Distribucion):
    def __init__(self, tasa): self.tasa = tasa
    def intervalo(self, rng): return float(rng.exponential(1/self.tasa))


class Determinista(Distribucion):
    def __init__(self, tasa): self.valor = 1/tasa
    def intervalo(self, rng): return self.valor


class Erlang(Distribucion):
    def __init__(self, tasa): self.tasa = tasa
    def intervalo(self, rng): return float(rng.gamma(2, 1/(2*self.tasa)))


# FACTORY: el resto del sistema no necesita conocer los constructores de estrategias
class FabricaSimulador:
    @staticmethod
    def distribucion(tipo, tasa):
        return {'exponencial':Exponencial,'determinista':Determinista,'erlang':Erlang}[tipo](tasa)

    @classmethod
    def crear(cls, config, puestos, semilla, numero_replica):
        return Simulador(config, puestos, semilla, numero_replica,
                        cls.distribucion(config.dist_llegada, config.llegada),
                        cls.distribucion(config.dist_servicio, config.servicio))


@dataclass
class ResultadoReplica:
    c: int
    replica: int
    semilla: int
    Wq: float
    Lq: float
    rho: float
    prob_espera: float
    usuarios_medidos: int
    llegadas: int
    pico_cola: int
    serie: list = field(default_factory=list)
    eventos: list = field(default_factory=list)


class ObservadorMetricas:
    """OBSERVER: acumula las medidas al recibir avisos del simulador."""
    def __init__(self, desde, hasta, puestos, guardar_serie):
        self.desde, self.hasta, self.puestos = desde, hasta, puestos
        self.t_anterior, self.cola, self.ocupados = 0., 0, 0
        self.area_cola = self.area_util = 0.
        self.suma_esperas = self.atendidos = self.esperaron = self.llegadas = 0
        self.serie = []
        self.paso = 2.
        self.siguiente_muestra = desde
        self.serie_fin = min(hasta, desde+240.)
        self.guardar_serie = guardar_serie

    def antes_de_evento(self, instante):
        inicio = max(self.t_anterior, self.desde)
        fin = min(instante, self.hasta)
        if fin > inicio:
            self.area_cola += (fin-inicio)*self.cola
            self.area_util += (fin-inicio)*self.ocupados/self.puestos
        if self.guardar_serie:
            while self.siguiente_muestra < instante and self.siguiente_muestra <= self.serie_fin + 1e-9:
                self.serie.append((round(self.siguiente_muestra,4), self.cola,self.ocupados,self.puestos))
                self.siguiente_muestra += self.paso
        self.t_anterior = instante

    def estado(self, cola, ocupados):
        self.cola, self.ocupados = cola, ocupados

    def llegada(self, instante):
        if self.desde <= instante < self.hasta: self.llegadas += 1

    def inicio_atencion(self, t, llegada):
        if self.desde <= llegada < self.hasta:
            self.suma_esperas += t - llegada
            self.atendidos += 1
            self.esperaron += int(t-llegada > 1e-12)

    def cerrar(self):
        self.antes_de_evento(self.hasta)
        tiempo = self.hasta-self.desde
        return (self.suma_esperas / self.atendidos if self.atendidos else 0.,
                self.area_cola / tiempo, self.area_util / tiempo,
                self.esperaron / self.atendidos if self.atendidos else 0.)


class Simulador:
    """Simula una cola FIFO y c puestos paralelos; primera réplica exporta datos NetLogo."""
    def __init__(self, config, puestos, semilla, numero_replica, llegadas, servicios):
        self.cfg, self.c, self.semilla, self.rep = config, puestos, semilla, numero_replica
        self.llegadas, self.servicios = llegadas, servicios

    def ejecutar(self):
        cfg, c = self.cfg, self.c
        rng_llegada = np.random.default_rng(np.random.SeedSequence([self.semilla, 1]))
        rng_servicio = np.random.default_rng(np.random.SeedSequence([self.semilla, 2]))
        obs = ObservadorMetricas(cfg.calentamiento, cfg.horizonte, c, self.rep == 1)
        eventos = []
        cola = deque()
        libres = list(range(1,c+1))
        from heapq import heapify
        heapify(libres)
        ocupados = {}                     # usuario -> puesto
        agenda = []                       # (tiempo, prioridad, orden, tipo, usuario, llegada)
        orden = 0
        nuevo_usuario = 0
        pico = 0
        registrar = self.rep == 1
        comienzo, fin = cfg.calentamiento, min(cfg.horizonte, cfg.calentamiento+120)
        estado_inicial_guardado = False

        def registrar_evento(t, tipo, user, puesto=0):
            if registrar and comienzo <= t < fin:
                eventos.append((round(t,8),tipo,user,puesto))

        def comienzo_eventos():
            nonlocal estado_inicial_guardado
            if not registrar or estado_inicial_guardado: return
            estado_inicial_guardado = True
            for usuario, puesto in sorted(ocupados.items(), key=lambda a:a[1]):
                eventos.append((comienzo,'inicio_atencion',usuario,puesto))
            for usuario, llegada in cola:
                eventos.append((comienzo,'inicio_cola',usuario,0))

        def agendar(t, tipo, user=0, llegada=0):
            nonlocal orden
            if t < cfg.horizonte:
                heappush(agenda, (t, 0 if tipo=='salida' else 1, orden, tipo, user, llegada))
                orden += 1

        def comenzar_atencion(user, llegada, tiempo):
            puesto = heappop(libres)
            ocupados[user] = puesto
            obs.inicio_atencion(tiempo, llegada)
            registrar_evento(tiempo, 'atencion', user, puesto)
            agendar(tiempo + self.servicios.intervalo(rng_servicio), 'salida', user)

        agendar(self.llegadas.intervalo(rng_llegada),'llegada')
        while agenda:
            t, _prior, _orden, tipo, user, llegada = heappop(agenda)
            if registrar and not estado_inicial_guardado and t >= comienzo: comienzo_eventos()
            obs.antes_de_evento(t)
            if tipo == 'llegada':
                nuevo_usuario += 1
                obs.llegada(t)
                registrar_evento(t,'llegada',nuevo_usuario)
                agendar(t+self.llegadas.intervalo(rng_llegada),'llegada')
                if libres and not cola:
                    comenzar_atencion(nuevo_usuario,t,t)
                else:
                    cola.append((nuevo_usuario,t))
                    pico = max(pico,len(cola))
            else:
                puesto = ocupados.pop(user)
                heappush(libres,puesto)
                registrar_evento(t,'salida',user,puesto)
                if cola:
                    siguiente, llegada_cola = cola.popleft()
                    comenzar_atencion(siguiente,llegada_cola,t)
            obs.estado(len(cola), len(ocupados))
        if registrar and not estado_inicial_guardado: comienzo_eventos()
        espera, lq, rho, prob = obs.cerrar()
        return ResultadoReplica(c,self.rep,self.semilla,espera,lq,rho,prob,
                                obs.atendidos,obs.llegadas,pico,obs.serie,eventos)
