"""Schemas Pydantic para validação determinística das extrações agênticas e APIs."""
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class CallLevels(BaseModel):
    zone: Optional[List[Optional[float]]] = None
    entry: Optional[Union[float, str]] = None
    stop: Optional[Union[float, str]] = None
    targets: List[Union[float, str]] = Field(default_factory=list)


class OperationalCall(BaseModel):
    """Schema validado de cada chamada operacional extraída em playbook/calls/*.jsonl."""
    date: str
    tweet_id: str
    asset: str
    action: Literal[
        "expectativa",
        "zona_monitorar",
        "aguardando_confirmacao",
        "entrada",
        "aumento",
        "realizacao_parcial",
        "saida_total",
        "stop",
        "invalidacao",
        "manutencao",
        "alerta_risco",
    ]
    direction: Literal["long", "short", "neutro", "caixa"]
    horizon: Literal["trade", "position", "indefinido"]
    hand: Optional[str] = None
    levels: CallLevels
    condition: Optional[str] = None
    quote: str
    refs: List[str] = Field(default_factory=list)
    source_type: Literal["post", "thread", "resposta", "imagem"]


class PillarScore(BaseModel):
    pts: int = Field(ge=0, le=25)
    desc: str


class DefensiveSetup(BaseModel):
    nome: str
    descricao: str
    alocacao_recomendada: str
    stop_loss: str
    gatilho_breakeven: str
    alocacao_risco: Optional[str] = None
    alocacao_caixa: Optional[str] = None


class ThesisAdvisoryReport(BaseModel):
    asset: str
    direction: Literal["long", "short"]
    confluence_score: int = Field(ge=0, le=100)
    confluence_verdict: str
    confluence_badge: Literal["GREEN", "YELLOW", "RED"]
    historical_win_rate: float
    historical_trades_count: int
    avg_max_gain_pct: float
    asymmetry_level: str
    hard_rule_alert: Optional[str] = None
    score_breakdown: Dict[str, PillarScore]
    o_que_aconteceu_no_historico: str
    por_que_importa: str
    o_que_fazer: str
    quando_arriscar_mais_sem_ruina: str
    setups_de_protecao: List[DefensiveSetup]


class LeaderboardEntry(BaseModel):
    rank: int
    asset: str
    direction: Literal["long", "short"]
    display_name: str
    summary: str
    score: int = Field(ge=0, le=100)
    badge: Literal["GREEN", "YELLOW", "RED"]
    status_tag: str
    status_icon: str
    win_rate: float
    trades_count: int
    asymmetry: str
    action_text: str
    breakdown: Dict[str, PillarScore]

