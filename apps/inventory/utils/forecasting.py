import pandas as pd
from django.db.models import Sum
from apps.orders.models import Order
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import matplotlib.pyplot as plt
from io import BytesIO
import base64


# ----------------------------------------
# 1. DATA ACCESS LAYER
# ----------------------------------------

def get_sales_timeseries(product_id, freq='D'):
    orders = (
        Order.objects
        .filter(
            product_id=product_id,
            is_deleted=False,
            status="Completed"
        )
        .values('order_date')
        .annotate(quantity_sold=Sum('quantity'))
        .order_by('order_date')
    )

    df = pd.DataFrame.from_records(orders)
    if df.empty:
        return None

    df['order_date'] = pd.to_datetime(df['order_date'])
    df.set_index('order_date', inplace=True)
    ts = df['quantity_sold'].resample(freq).sum().fillna(0)
    return ts


# ----------------------------------------
# 2. FORECAST MODELS
# ----------------------------------------

def arima_forecast(ts, steps=4):
    try:
        model = ARIMA(ts, order=(1, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=steps)
        return forecast, None
    except Exception as e:
        return None, str(e)

def ses_forecast(ts, steps=30):
    try:
        model = SimpleExpSmoothing(ts).fit()
        forecast = model.forecast(steps)
        return forecast, None
    except Exception as e:
        return None, str(e)


# ----------------------------------------
# 3. PLOTTING
# ----------------------------------------

def plot_forecast(ts, forecast, title="Forecast"):
    plt.figure(figsize=(10, 5))
    ts.plot(label='Historical', color='blue')
    forecast.plot(label='Forecast', color='orange', linestyle='--')
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Quantity Sold")
    plt.legend()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    graph = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return graph


# ----------------------------------------
# 4. MAIN FORECAST FUNCTION
# ----------------------------------------

def run_forecast(product_id, model_type='arima', steps=4, freq='W'):
    ts = get_sales_timeseries(product_id, freq=freq)
    if ts is None or len(ts) < 4:
        return None, 'Not enough sales data for forecasting.'

    if model_type == 'arima':
        forecast, err = arima_forecast(ts, steps=steps)
    else:
        forecast, err = ses_forecast(ts, steps=steps)

    if err:
        return None, f"Model failed: {err}"

    graph = plot_forecast(ts, forecast, title=f"{model_type.upper()} Forecast for Product {product_id}")
    return graph, None
