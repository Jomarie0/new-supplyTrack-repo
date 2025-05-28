import pandas as pd
from apps.orders.models import Order
from django.db.models import Sum
from datetime import datetime
from io import BytesIO
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
import base64

def get_sales_dataframe(product_id):
    # Only use non-deleted and completed orders within Mar–July
    orders = (
        Order.objects
        .filter(
            product_id=product_id,
            is_deleted=False,
            status="Completed",
            order_date__range=["2025-06-01", "2025-06-31",]
        )
        .values('order_date')
        .annotate(quantity_sold=Sum('quantity'))
        .order_by('order_date')
    )

    df = pd.DataFrame.from_records(orders)
    df.rename(columns={'order_date': 'date'}, inplace=True)
    return df

def forecast_stock_demand_from_orders(product_id, steps=4):
    df = get_sales_dataframe(product_id)

    if df.empty or len(df) < 4:
        return None, "Not enough sales data for forecasting."

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # Resample weekly
    ts = df['quantity_sold'].resample('W').sum()

    try:
        model = ARIMA(ts, order=(1, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=steps)
    except Exception as e:
        return None, f"Model error: {str(e)}"

    # Generate forecast plot
    plt.figure(figsize=(8, 4))
    ts.plot(label='Historical', color='blue')
    forecast.plot(label='Forecast', color='orange')
    plt.title(f"Stock Demand Forecast for Product {product_id}")
    plt.xlabel("Week")
    plt.ylabel("Units Sold")
    plt.legend()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    graph = base64.b64encode(image_png).decode('utf-8')
    plt.close()
    return graph, None
