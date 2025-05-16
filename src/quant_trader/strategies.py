# strategies.py

import backtrader as bt

class ScalpingStrategyV01(bt.Strategy):
    params = (
        ("volatility_period", 20), # Exemplo: período para cálculo de volatilidade (ex: ATR)
        ("entry_threshold_factor", 1.5), # Exemplo: fator para definir o gatilho de entrada baseado na volatilidade
        ("stop_loss_factor", 0.01), # Exemplo: 1% de stop loss
        ("take_profit_factor", 0.02), # Exemplo: 2% de take profit
        ("risk_per_trade_percent", 1), # Exemplo: arriscar 1% do capital por trade
        ("debug", False),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function for this strategy'''
        if self.params.debug or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Para rastrear ordens pendentes e preços de compra/venda
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.sellprice = None # Para registrar o preço de venda em uma operação de short (se aplicável no futuro)

        # Exemplo de indicador de volatilidade (Average True Range - ATR)
        self.atr = bt.indicators.AverageTrueRange(self.datas[0], period=self.params.volatility_period)

        self.log("Strategy Initialized", doprint=True)
        self.log(f"Params: Volatility Period: {self.params.volatility_period}, Entry Factor: {self.params.entry_threshold_factor}, SL: {self.params.stop_loss_factor}, TP: {self.params.take_profit_factor}", doprint=True)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Ordem submetida/aceita - nada a fazer
            self.log(f"ORDER SUBMITTED/ACCEPTED: Ref: {order.ref}, Type: {'Buy' if order.isbuy() else 'Sell'}, Size: {order.size}, Price: {order.price:.2f}")
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED, Ref: {order.ref}, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell(): # Venda
                self.log(f"SELL EXECUTED, Ref: {order.ref}, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
                self.sellprice = order.executed.price # Atualiza preço de venda para short

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"ORDER CANCELED/MARGIN/REJECTED: Ref: {order.ref}, Status: {order.getstatusname()}")

        # Resetar ordem após ser processada
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")

    def next(self):
        # Checar se há uma ordem pendente
        if self.order:
            return

        current_atr = self.atr[0]
        entry_signal_threshold = current_atr * self.params.entry_threshold_factor
        
        # Lógica de Scalping (Exemplo Simplificado - precisa ser refinado)
        # Esta é uma lógica muito básica e precisa ser desenvolvida com base em uma estratégia de scalping real.
        # Por exemplo, entrar se o preço se mover X vezes o ATR em um curto período.

        # Se não estiver no mercado
        if not self.position:
            # Exemplo de condição de entrada (COMPRA)
            # Se o preço subir mais que o entry_signal_threshold em relação à abertura da barra atual
            if self.dataclose[0] > self.dataopen[0] + entry_signal_threshold:
                self.log(f"BUY CREATE, Price: {self.dataclose[0]:.2f}, ATR: {current_atr:.2f}, Entry Threshold: {entry_signal_threshold:.2f}")
                
                # Calcular tamanho da posição baseado no risco
                cash = self.broker.get_cash()
                size_risk_based = (cash * (self.params.risk_per_trade_percent / 100)) / (self.dataclose[0] * self.params.stop_loss_factor)
                # size = int(size_risk_based) # Ajustar para o mínimo negociável do ativo
                size = 1 # Placeholder, precisa ajustar para o ativo real

                # Definir preços de stop loss e take profit
                stop_price = self.dataclose[0] * (1 - self.params.stop_loss_factor)
                take_profit_price = self.dataclose[0] * (1 + self.params.take_profit_factor)

                # Criar ordem de compra com stop loss e take profit (Bracket Order)
                # Backtrader não tem bracket order nativa para todas as corretoras.
                # Uma forma é enviar a ordem de entrada e, após execução, enviar ordens OCO (One-Cancels-Other) para stop e profit.
                # Para simplificar, vamos enviar a ordem de compra e gerenciar o stop/profit manualmente ou com ordens separadas.
                self.order = self.buy(size=size)
                # Exemplo de como poderia ser com ordens separadas (precisa de lógica para gerenciar se uma é atingida)
                # self.buy_bracket(price=self.datas[0].close[0], 
                #                  stopprice=stop_price, 
                #                  limitprice=take_profit_price,
                #                  size=size)
                self.log(f"Buy order created at {self.dataclose[0]:.2f} with SL: {stop_price:.2f} and TP: {take_profit_price:.2f}")

        else: # Se já estiver no mercado (comprado)
            # Lógica de saída
            if self.dataclose[0] <= self.buyprice * (1 - self.params.stop_loss_factor):
                self.log(f"STOP LOSS HIT, Price: {self.dataclose[0]:.2f}")
                self.order = self.sell(size=self.position.size) # Fechar posição
            elif self.dataclose[0] >= self.buyprice * (1 + self.params.take_profit_factor):
                self.log(f"TAKE PROFIT HIT, Price: {self.dataclose[0]:.2f}")
                self.order = self.sell(size=self.position.size) # Fechar posição

    def stop(self):
        self.log(f"(Volatility Period {self.params.volatility_period}) Ending Value {self.broker.getvalue():.2f}", doprint=True)

# Para adicionar mais estratégias, crie novas classes aqui.

