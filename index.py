import requests
from bs4 import BeautifulSoup

from flask import Flask, render_template, request, make_response, jsonify
from datetime import datetime

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# 判斷是在 Vercel 還是本地
if os.path.exists('serviceAccountKey.json'):
    # 本地環境：讀取檔案
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    # 雲端環境：從環境變數讀取 JSON 字串
    firebase_config = os.getenv('FIREBASE_CONFIG')
    cred_dict = json.loads(firebase_config)
    cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)

app = Flask(__name__)

@app.route("/")
def index():
    link = "<h1>歡迎進入李羿慧的網站20260409</h1>"
    link +="<a href = /mis>課程</a><hr>"
    link +="<a href = /today>現在日期時間</a><hr>"
    link +="<a href = /me>關於我</a><hr>"
    link +="<a href = /welcome?u=zhe&d=靜宜資管&c=資訊管理導論>Get傳值</a><hr>"
    link +="<a href = /account>POST傳值(帳號密碼)</a><hr>"
    link +="<a href = /math>次方與根號計算</a><hr>"
    link +="<a href=/read>讀取Firestore資料</a><hr>"
    link +="<a href=/read2>讀取Firestore資料(關鍵字查詢)</a><hr>"
    link += "<a href=/search>讀取Firestore資料(關鍵字查詢:input)</a><hr>"
    link += "<a href=/spider>爬取子青老師本學期課程</a><hr>"
    link += "<a href=/movie>爬取即將上映電影</a><hr>"
    link += "<a href=/spiderMovie>爬取即將上映電影到資料庫</a><hr>"
    link += "<a href=/searchMovie>資料庫電影查詢關鍵字</a><hr>"
    link += "<a href=/road>台中市十大肇事路口</a><hr>"
    link += "<a href=/weather>查詢各縣市目前天氣及降雨機率</a><hr>"
    link += "<a href=/rate>本週新片進DB</a><hr>"
    link += "<a href=/webdemo>聊天機器人</a><hr>"
    return link 

@app.route("/webdemo")
def webdemo():
    return render_template("webdemo.html")

@app.route("/webhook", methods=["POST"])
def webhook():
    # 取得 Dialogflow 傳來的請求資料
    req = request.get_json(force=True)
   
    # 為了避免 KeyError 當機，改用 .get() 來安全取值
    action = req.get("queryResult", {}).get("action", "")
   
    # 設定一個預設回覆
    info = "抱歉，我目前無法處理這個動作喔！"
   
    if action == "rateChoice":
        # 取得使用者輸入的分級 (因為你說 Dialogflow 已經設定好同義詞轉換了)
        rate = req.get("queryResult", {}).get("parameters", {}).get("rate", "")
       
        info = "我是李羿慧設計的機器人，您選擇的電影分級是：" + rate + "，本週相關電影有：\n\n"

        # 連線到 Firestore 資料庫
        db = firestore.client()
        # 注意：這裡要確定對應到你有爬蟲寫入資料的那個集合名稱
        collection_ref = db.collection("本週新片含分級")
        docs = collection_ref.get()
       
        result = ""
        count = 0
       
        # 開始迴圈比對資料庫
        for doc in docs:
            movie_data = doc.to_dict()
            # 比對 Dialogflow 傳來的分級是否包含在資料庫的 rate 欄位中
            if rate in movie_data.get("rate", ""):
                result += "🎬 片名：" + movie_data.get("title", "") + "\n"
                #result += "🔗 介紹：" + movie_data.get("hyperlink", "") + "\n\n"
                count += 1
       
        # 判斷有沒有找到符合條件的電影
        if count > 0:
            info += result
        else:
            info += "目前資料庫中找不到符合此分級的電影喔！"

    # 將整理好的字串包裝成 Dialogflow 看得懂的 JSON 格式回傳
    return make_response(jsonify({"fulfillmentText": info}))

@app.route("/rate")
def rate():
    #本週新片
    url = "https://www.atmovies.com.tw/movie/new/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text[5:]
    print(lastUpdate)
    print()

    result=sp.select(".filmList")

    for x in result:
        title = x.find("a").text
        introduce = x.find("p").text

        movie_id = x.find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw/movie/" + movie_id
        picture = "https://www.atmovies.com.tw/photo101/" + movie_id + "/pm_" + movie_id + ".jpg"

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r != None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        t = x.find(class_="runtime").text

        t1 = t.find("片長")
        t2 = t.find("分")
        showLength = t[t1+3:t2]

        t1 = t.find("上映日期")
        t2 = t.find("上映廳數")
        showDate = t[t1+5:t2-8]

        doc = {
            "title": title,
            "introduce": introduce,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": int(showLength),
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        db = firestore.client()
        doc_ref = db.collection("本週新片含分級").document(movie_id)
        doc_ref.set(doc)
    return "本週新片已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate

@app.route("/weather")
def weather():
    city = request.args.get("city") 
    
    R = """
    <form action="/weather" method="GET">
        <h1>縣市天氣及降雨機率查詢</h1>
        <input type="text" name="city" placeholder="請輸入縣市名稱（例如：臺中市）">
        <button type="submit">查詢</button>
    </form>
    <hr>
    """

    if city:
        city = city.replace("台", "臺")
        url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=rdec-key-123-45678-011121314&format=JSON&locationName=" + city
        try:
            response = requests.get(url)
            data = response.json() 
            
            location_data = data["records"]["location"][0]
            weather_element = location_data["weatherElement"]
            
            weather_state = weather_element[0]["time"][0]["parameter"]["parameterName"]
            rain_chance = weather_element[1]["time"][0]["parameter"]["parameterName"]
            
            result = f"<h2>{city} 最新天氣預報</h2>"
            result += f"<p>天氣狀況：{weather_state}</p>"
            result += f"<p>降雨機率：{rain_chance}%</p>"
            
            return R + result
            
        except Exception as e:
            return R + f"<p style='color:red;'>查詢失敗：請檢查縣市名稱是否正確</p>"
    R += "<br><a href='/'>返回首頁</a>"
    return R

@app.route("/road")
def road():
    R = "<h1>台中市十大肇事路口(113年10月)作者:李羿慧</h1><br>"

    url = "https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=a1b899c0-511f-4e3d-b22b-814982a97e41"
    Data = requests.get(url)
    JsonData = json.loads(Data.text)
    for item in JsonData:
        R += item["路口名稱"] + ",原因:" + item["主要肇因"] + ",件數:" + item["總件數"] + "<br>"

    return R

@app.route("/searchMovie", methods=["GET"])
def searchMovie():
    keyword = request.args.get("q")  
    R = """
        <form action="/searchMovie" method="GET">
        <h1>電影資料庫關鍵字查詢</h1>
        <input type="text" name="q" placeholder="請輸入片名關鍵字">
        <button type="submit">查詢</button>
        </form>
        <hr>
    """ 
    
    return R
    found = False
    count = 0
    results_content = "" 

    if keyword:
        db = firestore.client()
        collection_ref = db.collection("電影2B")
        docs = collection_ref.get()

    for doc in docs:
        movie_data = doc.to_dict()
        title = movie_data.get("title", "")

    if keyword in title:  
        found = True
        count += 1
        
        movie_id = doc.id
        picture = movie_data.get("picture", "")
        hyperlink = movie_data.get("hyperlink", "#")
        showDate = movie_data.get("showDate", "未提供")

        results_content += f"<b>編號:</b> {movie_id}<br>"
        results_content += f"<b>片名:</b> {title}<br>"
        results_content += f"<b>上映日期:</b> {showDate}<br>"
        results_content += f"<a href='{hyperlink}' target='_blank'>查看電影介紹</a><br>"
        results_content += f"<img src='{picture}' width='150' style='margin-top:10px;'><br><hr>"

        if found:
            R = f"<h4>找到 {count} 部符合「{keyword}」的電影:</h4>" + R + results_content
        else:
            R += f"<p>抱歉，資料庫找不到包含「{keyword}」的電影。</p>"
    
    R += "<br><a href='/'>返回首頁</a>"
    return R

@app.route("/spiderMovie")
def spiderMovie():
    R = ""

    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"

    sp = BeautifulSoup(Data.text, "html.parser")

    lastUpdate = sp.find(class_="smaller09").text.replace("更新時間：", "")
    result = sp.select(".filmListAllX li")
    db = firestore.client()
    total = 0

    for item in result:
        total += 1
        movie_id = item.find("a").get("href").replace("/movie/", "").replace("/", "")
        title = item.find(class_="filmtitle").text
        picture = "http://www.atmovies.com.tw" + item.find("img").get("src")
        hyperlink = "http://www.atmovies.com.tw" + item.find("a").get("href")
        showDate = item.find(class_="runtime").text[5:15]

        doc = {
            "title": title,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "lastUpdate": lastUpdate
        }

        doc_ref = db.collection("電影2B").document(movie_id)
        doc_ref.set(doc)

    R = "網站最近更新日期：" + lastUpdate + "<br>"
    R += "總共爬取" + str(total) + "部電影到資料庫" + "<br>"

    R += "<br><a href='/'>返回首頁</a>"
    return R

@app.route("/movie", methods=["GET", "POST"])
def movie1():
    if request.method == "POST":
        keyword = request.values.get("keyword")
       
        url = "https://www.atmovies.com.tw/movie/next/"
        Data = requests.get(url)
        Data.encoding = "utf-8"
        sp = BeautifulSoup(Data.text, "html.parser")
        result = sp.select(".filmListAllX li")
       
        R = f"<h2>您搜尋的關鍵字是：{keyword}</h2>"
        found = False
       
        for item in result:
            movie_name = item.find("img").get("alt")
            
            if keyword in movie_name:
                found = True
                introduce = "https://www.atmovies.com.tw" + item.find("a").get("href")
                post = "https://www.atmovies.com.tw" + item.find("img").get("src")
                
                R += f"<a href='{introduce}' target='_blank'>{movie_name}</a><br>"
                R += f"<img src='{post}' style='width:200px;'><br><br>"
    if request.method == "POST":
        
        if not found:
            R += "<p>抱歉，查無包含此關鍵字的即將上映電影。</p>"
            
        return R + "<br><a href='/movie'>重新查詢</a> | <a href='/'>返回首頁</a>"

    else:
        html = """
            <h2>即將上映電影查詢</h2>
            <form action="/movie" method="POST">
                請輸入電影片名關鍵字：
                <input type="text" name="keyword" required>
                <button type="submit">搜尋</button>
            </form>
            <br><a href="/">返回首頁</a>
        """
        return html

@app.route("/spider")
def spider():
    Result = ""
    url = "https://www1.pu.edu.tw/~tcyang/course.html"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select(".team-box a")

    for i in result:
        Result += i.text + i.get("href") + "<br>"
    return Result

@app.route("/search", methods=["GET", "POST"])
def search():
    results = []  # 準備一個空清單來裝所有符合條件的老師
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword", "")
        if keyword:
            db = firestore.client()
            collection_ref = db.collection("靜宜資管")
            docs = collection_ref.get()  # 抓取所有文件
           
            for doc in docs:
                teacher = doc.to_dict()
                # 模糊比對：只要老師姓名裡包含關鍵字，就加入清單
                if keyword in teacher.get("name", ""):
                    results.append(teacher)  # 這裡會不斷累積符合條件的人
   
    # 將包含「多位老師」的清單傳給網頁
    return render_template("search.html", results=results, keyword=keyword)


@app.route("/read")
def read():
    Result = ""
    db = firestore.client()
    collection_ref = db.collection("靜宜資管")    
    docs = collection_ref.order_by("lab", direction=firestore.Query.DESCENDING).get()    
    for doc in docs:         
        Result += str(doc.to_dict()) + "<br>"    
    return Result

@app.route("/read2")  
def read2():
    Result = ""
    keyword = "李"
    db = firestore.client()
    collection_ref = db.collection("靜宜資管")
    docs = collection_ref.get()
    for doc in docs:
        teacher = doc.to_dict()
        if keyword in teacher["name"]:
            Result += str(teacher) + "<br>"
    
    if Result == "":
       Result = "抱歉,查無此關鍵字姓名老師資料"
    return Result

@app.route("/mis")
def course():
    return "<h1>資訊管理導論</h1><a href=/>返回首頁</a>"

@app.route("/today")
def today():
    now = datetime.now()
    return render_template("today.html", datetime = str(now))

@app.route("/me")
def me():
    return render_template("mis2026b.html")

@app.route("/welcome",methods=["GET"])
def welcome():
    user = request.values.get("u")
    d = request.values.get("d")
    c = request.values.get("c")
    return render_template("welcome.html", name = user, dep = d, course = c)

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]
        result = "您輸入的帳號是：" + user + "; 密碼為：" + pwd 
        return result
    else:
        return render_template("account.html")

@app.route("/math", methods=["GET", "POST"])
def math():
    x_val = request.form.get("x")
    y_val = request.form.get("y")
    opt = request.form.get("opt")

    if request.method == "POST":
        try:
            x = float(x_val)
            y = float(y_val)

            if opt == "∧":
                result = x ** y
            elif opt == "√":
                if y == 0:
                    result = "數學不能開0次方根"
                else:
                    result = x ** (1/y)
            else:
                result = "請選擇運算符號"
        except ValueError:
            result = "請輸入有效的數字"
        return render_template("math.html", final_result= result)
    return render_template("math.html")

if __name__ == "__main__":
    app.run(debug=True)