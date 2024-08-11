from flask import Flask, render_template, request
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import json
from io import BytesIO
import base64

# 비상호작용 백엔드 사용
matplotlib.use('Agg')

app = Flask(__name__)

# JSON에서 데이터 로드
with open('assessment.json') as f:
    data = json.load(f)

# JSON 데이터를 pandas DataFrame으로 변환
df = pd.DataFrame(data)
df['Date'] = pd.to_datetime(df['Date'])  # 'Date'가 datetime 형식인지 확인

def create_graph(selected_index=None, num_dates=5, start_date=None, end_date=None):
    # 지정된 날짜 범위로 데이터 필터링
    filtered_df = df.copy()
    if start_date:
        filtered_df = filtered_df[filtered_df['Date'] >= pd.to_datetime(start_date)]
    if end_date:
        filtered_df = filtered_df[filtered_df['Date'] <= pd.to_datetime(end_date)]
    
    sorted_df = filtered_df.sort_values(by='Date')  # 날짜별로 정렬
    recent_data = sorted_df.tail(num_dates)  # 범위 내에서 가장 최근 날짜 선택

    dates = recent_data['Date'].dt.strftime('%Y-%m-%d')  # x축에 사용할 문자열로 날짜 형식 지정
    indices = list(df.columns[1:])  # 열에서 인덱스 이름 추출 ('Date' 제외)

    # 각 플롯에 대해 새 그림 생성
    fig, ax = plt.subplots(figsize=(12, 10))  # 더 나은 제어를 위해 서브플롯 사용
    if selected_index and selected_index in indices:
        # 선택한 인덱스만 플롯
        ax.plot(dates, recent_data[selected_index], label=selected_index, marker='o')
    else:
        # 잘못된 인덱스가 선택된 경우 모든 인덱스 플롯
        for index in indices:
            ax.plot(dates, recent_data[index], label=index, marker='o')
    ax.set_xlabel("Date")
    ax.set_ylabel("Level")
    ax.set_ylim(1, 9)
    ax.set_xticks(dates)
    ax.set_xticklabels(dates, rotation=45)
    ax.legend()

    # 플롯을 메모리에 PNG 이미지로 저장
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)  # 그림을 적절히 닫기
    buf.seek(0)

    # 이미지를 base64로 인코딩하여 반환
    return base64.b64encode(buf.getvalue()).decode('utf-8')

@app.route('/', methods=['GET', 'POST'])
def index():
    selected_index = request.form.get('index_selector')
    num_dates = int(request.form.get('num_dates', 5))  # 최근 날짜 수 가져오기
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    # 사용자 선택에 따라 그래프 생성
    image = create_graph(selected_index, num_dates, start_date, end_date)

    indices = list(df.columns[1:])  # 열에서 인덱스 이름 추출
    return render_template('myreport.html', image_data=image, indices=indices, selected_index=selected_index, num_dates=num_dates, start_date=start_date, end_date=end_date)

if __name__ == '__main__':
    app.run(debug=True)
