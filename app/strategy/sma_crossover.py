from dataclasses import dataclass
import pandas as pd
from typing import Optional
import logging


@dataclass
class SmaParams:
    short: int = 7
    long: int = 21
    # seuils : au moins X USDT d'ecart OU X% du prix
    min_gap_usdt: float = 50.0
    min_gap_pct: float = 0.0005  # 0.05%
    confirm_bars: int = 3


class SmaCrossover:
    """
    Strategie SMA crossover avec:
      - seuil dynamique: max(min_gap_usdt, price * min_gap_pct)
      - confirmation: N bougies apres detection du croisement
    API:
      - compute(df) -> df avec colonnes 'sma_short', 'sma_long'
      - signal(df) -> "BUY" | "SELL" | None
    Etats internes:
      - _cross_dir: "UP" | "DOWN" | None
      - _confirm_count: int
      - last_info: dict pour le "pourquoi"
    """
    def __init__(self, params: SmaParams, log: Optional[logging.Logger] = None):
        self.p = params
        self.log = log
        self._cross_dir: Optional[str] = None
        self._confirm_count: int = 0
        self.last_info = {}

    # --- utils ---
    def _dynamic_threshold(self, price: float) -> float:
        return max(float(self.p.min_gap_usdt), float(price) * float(self.p.min_gap_pct))

    # --- core ---
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["sma_short"] = df["close"].rolling(window=self.p.short, min_periods=self.p.short).mean()
        df["sma_long"]  = df["close"].rolling(window=self.p.long,  min_periods=self.p.long).mean()
        return df

    def signal(self, df: pd.DataFrame) -> Optional[str]:
        """
        Evalue le dernier tick de df. Remplit self.last_info.
        Retourne "BUY", "SELL", ou None.
        """
        if len(df) < max(self.p.short, self.p.long) + 1:
            self.last_info = {
                "why": "Pas assez de donnees pour calculer les SMA.",
                "trend": "?",
                "cross": "none",
                "confirm_count": 0,
                "confirm_needed": self.p.confirm_bars,
                "gap_needed": None,
            }
            if self.log:
                self.log.info("[SMA] Donnees insuffisantes (need >= %d bougies).",
                              max(self.p.short, self.p.long))
            return None

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price = float(last["close"])
        sma_s = float(last["sma_short"])
        sma_l = float(last["sma_long"])
        prev_s = float(prev["sma_short"]) if pd.notna(prev["sma_short"]) else None
        prev_l = float(prev["sma_long"])  if pd.notna(prev["sma_long"])  else None

        # Si pas encore de SMA, on sort
        if pd.isna(sma_s) or pd.isna(sma_l) or prev_s is None or prev_l is None:
            self.last_info = {
                "why": "En attente que les SMA soient disponibles.",
                "trend": "?",
                "cross": "none",
                "confirm_count": 0,
                "confirm_needed": self.p.confirm_bars,
                "gap_needed": None,
            }
            return None

        gap = sma_s - sma_l
        prev_gap = prev_s - prev_l
        abs_gap = abs(gap)

        threshold = self._dynamic_threshold(price)
        trend = "bullish" if gap > 0 else "bearish"

        # Detection du croisement sur la derniere bougie terminee
        cross = "none"
        if prev_gap <= 0 < gap:
            cross = "golden"  # short passe au-dessus du long
            self._cross_dir = "UP"
            self._confirm_count = 0  # on attend confirmations APRES ce point
        elif prev_gap >= 0 > gap:
            cross = "death"   # short passe en-dessous du long
            self._cross_dir = "DOWN"
            self._confirm_count = 0

        # Si pas de nouveau cross, mais on est en phase de confirmation
        if self._cross_dir:
            # Tant que la direction et le seuil sont respectes, on compte
            dir_ok = (self._cross_dir == "UP" and gap > 0) or (self._cross_dir == "DOWN" and gap < 0)
            if dir_ok and abs_gap >= threshold:
                self._confirm_count += 1
            else:
                # conditions cassees -> on annule la phase de confirmation
                self._cross_dir = None
                self._confirm_count = 0

        # Construction du message "pourquoi"
        self.last_info = {
            "trend": trend,
            "cross": cross,
            "confirm_count": self._confirm_count,
            "confirm_needed": self.p.confirm_bars,
            "gap_needed": threshold,
            "why": "",
            "near_cross": False,
        }

        # Alerte "croisement proche": inversion de signe entre prev_gap et gap,
        # mais seuil non encore atteint (ou confirmation pas encore faite)
        if (gap > 0 and prev_gap < 0) or (gap < 0 and prev_gap > 0):
            if abs_gap < threshold:
                self.last_info["near_cross"] = True

        # Cas 1: seuil non atteint -> pas de signal
        if abs_gap < threshold:
            self.last_info["why"] = "Ecart insuffisant: |gap|=%.2f < seuil=%.2f." % (abs_gap, threshold)
            return None

        # Cas 2: seuil ok mais on n'est pas en phase "post-cross" -> pas de signal
        if self._cross_dir is None:
            self.last_info["why"] = "Aucun croisement actif. Seuil ok mais besoin d'un croisement recent."
            return None

        # Cas 3: en phase post-cross, mais confirmations insuffisantes
        if self._confirm_count < self.p.confirm_bars:
            self.last_info["why"] = "Confirmation insuffisante: %d/%d." % (
                self._confirm_count, self.p.confirm_bars
            )
            return None

        # Cas 4: tout est valide -> signal
        signal = "BUY" if self._cross_dir == "UP" else "SELL"
        # reset pour la prochaine sequence
        self._cross_dir = None
        self._confirm_count = 0
        self.last_info["why"] = "Conditions remplies (seuil et confirmations)."
        return signal
