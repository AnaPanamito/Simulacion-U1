"""CAPA DOMINIO: configuración (Builder), fórmulas M/M/c y SymPy."""
from __future__ import annotations
from dataclasses import dataclass
from math import factorial, inf, isfinite


@dataclass(frozen=True)
class Configuracion:
    llegada: float = 0.8              # lambda: usuarios/min
    servicio: float = 1 / 3          # mu: usuarios/min/puesto
    puestos: int = 4
    replicas: int = 30
    horizonte: float = 12000
    calentamiento: float = 1200
    semilla: int = 2026
    espera_maxima: float = 2.0
    utilizacion_maxima: float = 0.85
    dist_llegada: str = 'exponencial'
    dist_servicio: str = 'exponencial'

    def __post_init__(self):
        if not all(isfinite(v) and v > 0 for v in (self.llegada, self.servicio)):
            raise ValueError('lambda y mu deben ser números positivos y finitos')
        if self.puestos < 1 or self.replicas < 1 or self.semilla < 0:
            raise ValueError('puestos y réplicas deben ser positivos, semilla no negativa')
        if not 0 <= self.calentamiento < self.horizonte:
            raise ValueError('Debe cumplirse 0 <= calentamiento < horizonte')
        if self.espera_maxima <= 0 or not 0 < self.utilizacion_maxima < 1:
            raise ValueError('Umbrales inválidos')
        if self.dist_llegada not in ('exponencial', 'determinista', 'erlang') or self.dist_servicio not in ('exponencial','determinista','erlang'):
            raise ValueError('Distribución desconocida')

    @property
    def es_mmc(self):
        return self.dist_llegada == self.dist_servicio == 'exponencial'


class ConstructorEscenario:
    """BUILDER: evita crear escenarios con parámetros dispersos."""
    def __init__(self):
        self.valores = {}

    def tasas(self, llegada, servicio):
        self.valores.update(llegada=llegada, servicio=servicio)
        return self

    def experimentos(self, replicas=30, horizonte=12000, calentamiento=1200, semilla=2026):
        self.valores.update(replicas=replicas, horizonte=horizonte, calentamiento=calentamiento, semilla=semilla)
        return self

    def limites(self, espera=2.0, utilizacion=0.85):
        self.valores.update(espera_maxima=espera, utilizacion_maxima=utilizacion)
        return self

    def distribuciones(self, llegada='exponencial', servicio='exponencial'):
        self.valores.update(dist_llegada=llegada, dist_servicio=servicio)
        return self

    def construir(self):
        return Configuracion(**self.valores)


def teoria_mmc(llegada: float, servicio: float, puestos: int) -> dict:
    """Cálculos M/M/c: rho, P0, Lq, Wq y probabilidad de esperar."""
    if llegada <= 0 or servicio <= 0 or puestos < 1:
        raise ValueError('Tasas positivas y puestos >= 1 requeridos')
    a = llegada / servicio
    rho = llegada / (puestos * servicio)
    base = {'c':puestos, 'rho':rho, 'a':a, 'estable':rho < 1}
    if rho >= 1:
        return {**base, 'P0':None, 'Lq':inf, 'Wq':inf, 'P_espera':None}
    p0 = 1 / (sum(a**n / factorial(n) for n in range(puestos))
              + a**puestos / (factorial(puestos) * (1 - rho)))
    lq = p0 * a**puestos * rho / (factorial(puestos) * (1-rho)**2)
    return {**base, 'P0':p0, 'Lq':lq, 'Wq':lq/llegada,
            'P_espera':p0 * a**puestos / (factorial(puestos)*(1-rho))}


def comprobar_con_sympy(llegada, servicio, puestos, destino):
    """Comprueba simbólicamente la espera; no cambia los resultados numéricos."""
    from sympy import symbols, factorial as sf, Sum, N
    lam, mu, c = symbols('lambda mu c', positive=True)
    n = symbols('n', integer=True, nonnegative=True)
    a, rho = lam/mu, lam/(c*mu)
    p0 = 1 / (Sum(a**n/sf(n), (n, 0, c-1)) + a**c/(sf(c)*(1-rho)))
    wq = (p0*a**c*rho / (sf(c)*(1-rho)**2)) / lam
    lineas = ['MODELO SIMBÓLICO M/M/c (SymPy)', f'rho = {rho}', f'P0 = {p0}', f'Wq = {wq}', '',
              'Solo se evalúan escenarios estables:']
    for count in puestos:
        teor = teoria_mmc(llegada, servicio, count)
        if not teor['estable']:
            lineas.append(f'c={count}: INESTABLE (rho={teor["rho"]:.6f})')
            continue
        sym = float(N(wq.subs({lam:llegada, mu:servicio, c:count}).doit(), 12))
        if abs(sym-teor['Wq']) > 1e-7:
            raise ArithmeticError('SymPy no coincide con la fórmula numérica')
        lineas.append(f'c={count}: Wq SymPy={sym:.6f} min | Wq Python={teor["Wq"]:.6f} min')
    destino.write_text('\n'.join(lineas)+'\n', encoding='utf-8')
