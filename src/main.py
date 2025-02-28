from datetime import datetime
import os
import threading
import time

from flask import Flask, redirect, render_template, request, send_from_directory
import schedule
from config import CHECK_INTERVAL, PUBLIC_FOLDER, SERVER_PORT, WATCH_FOLDER
from db import db_query_all, db_execute, db_query_one
from pdf import convert_pdf_to_jpg

app = Flask(__name__)


def convert_job():
    """
    从数据库检索未处理的 pdf, 转换成图片
    """
    print("start schedule job")
    while (True):
        try:
            t = datetime.now()
            items = db_query_all("""
                select r._id, p.recordid, p.anauploaddate, p.reviewuploaddate from patient p left join report r on p.reqid = r.reqid 
                where
                (p.anauploaddate is not null and (r.imgupdate is null or p.anauploaddate > r.imgupdate) ) or 
                (p.reviewuploaddate is not null and (r.imgupdate is null or p.reviewuploaddate  > r.imgupdate))
                limit 10
            """)
            if len(items) == 0:
                break

            for item in items:
                (rid, record_id, anauploaddate, reviewuploaddate) = item
                # print(f"start process {record_id}")
                ana_pdf_path = os.path.join(
                    WATCH_FOLDER, f"{record_id}_anareport.pdf")
                review_pdf_path = os.path.join(
                    WATCH_FOLDER, f"{record_id}_reviewreport.pdf")
                ana_list = None
                review_list = None
                if anauploaddate is not None and os.path.exists(ana_pdf_path):
                    print(f"processing {record_id} ana")
                    pages = convert_pdf_to_jpg(ana_pdf_path, os.path.join(
                        WATCH_FOLDER, 'images', record_id), 'ana')
                    ana_list = ','.join(
                        map(lambda x: f"{record_id}/{x}", pages))

                if reviewuploaddate is not None and os.path.exists(review_pdf_path):
                    print(f"processing {record_id} review")
                    pages = convert_pdf_to_jpg(review_pdf_path, os.path.join(
                        WATCH_FOLDER, 'images', record_id), 'review')
                    review_list = ','.join(
                        map(lambda x: f"{record_id}/{x}", pages))
                if ana_list is not None or review_list is not None:
                    db_execute("""
                            update report 
                            set imgupdate = %s, anaimglist = %s, reviewimglist = %s
                            where _id = %s
                        """, (t, ana_list, review_list, rid))
                    print(
                        f"update {record_id}, ana: {ana_list}, review: {review_list}")
            # print("done schedule job")
        except Exception as e:
            print(f"schedule job failed: {str(e)}")

    time.sleep(1)


def run_schedule():
    convert_job()
    while True:
        schedule.run_pending()
        time.sleep(1)


def start_schedule():
    """
    轮询转换pdf
    """
    schedule.every(CHECK_INTERVAL).minutes.do(convert_job)
    threading.Thread(target=run_schedule, daemon=True).start()


@app.route('/')
def index():
    reqid = request.args.get('reqid')
    type = request.args.get('type')
    # if reqid is None:
    #     return redirect("/?reqid=测试的-0-0000&type=reviewreport")
    (imgupdate, anaimglist, reviewimglist) = db_query_one("""
        select r.imgupdate,r.anaimglist, r.reviewimglist from report r where r.reqid = %s
    """, (reqid,))
    items = anaimglist if type == "anareport" else reviewimglist

    return render_template('index.html', items=items.split(','), time=int(imgupdate.timestamp()))
    # return send_from_directory('static', 'index.html')


@app.route('/img/<recordid>/<filename>')
def serve_image(recordid, filename):
    return send_from_directory(os.path.join(WATCH_FOLDER, "images", recordid), filename)


if __name__ == "__main__":

    os.makedirs(WATCH_FOLDER, exist_ok=True)
    os.makedirs(PUBLIC_FOLDER, exist_ok=True)

    start_schedule()

    app.run(
        host="0.0.0.0",
        port=SERVER_PORT,
        debug=True,
        use_reloader=False,
        threaded=True
    )
