import os
import time
import threading
import schedule
import configparser
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import mysql.connector
from pdf2image import convert_from_path

app = Flask(__name__)

def load_config():
    """加载并验证配置文件"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件未找到: {config_path}")

    config.read(config_path)
    
    required_sections = {
        'database': ['host', 'user', 'password', 'database', 'port'],
        'paths': ['watch_folder'],
        'settings': ['check_interval', 'max_retries', 'retry_interval'],
        'server': ['host', 'port']
    }
    
    for section, keys in required_sections.items():
        if not config.has_section(section):
            raise ValueError(f"缺少配置段落: [{section}]")
        for key in keys:
            if not config.has_option(section, key):
                raise ValueError(f"段落 [{section}] 缺少配置项: {key}")
    
    return config

try:
    config = load_config()
except Exception as e:
    print(f"配置加载失败: {str(e)}")
    exit(1)

# 配置信息（保持不变）
DB_CONFIG = {
    'host': config.get('database', 'host'),
    'user': config.get('database', 'user'),
    'password': config.get('database', 'password'),
    'database': config.get('database', 'database'),
    'port': config.getint('database', 'port'),
    'autocommit': True
}

SERVER_HOST = config.get('server', 'host')
SERVER_PORT = config.getint('server', 'port')
WATCH_FOLDER = os.path.expanduser(config.get('paths', 'watch_folder'))
CHECK_INTERVAL = config.getint('settings', 'check_interval')
MAX_RETRIES = config.getint('settings', 'max_retries')
RETRY_INTERVAL = config.getint('settings', 'retry_interval')

def init_database():
    """初始化数据库表结构"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report (
                reqid VARCHAR(255) PRIMARY KEY,
                jpgurl TEXT,
                totalpages INT,
                createtime DATETIME,
                lastupdate DATETIME
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient (
                recordid VARCHAR(255) PRIMARY KEY,
                reqid VARCHAR(255),
                FOREIGN KEY (reqid) REFERENCES report(reqid)
            )
        """)
        
        conn.commit()
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        raise
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

class PDFProcessor:
    @staticmethod
    def generate_base_url(reqid, total_pages):
        return f"http://{SERVER_HOST}:{SERVER_PORT}/report/jpg?reqid={reqid}&totalpages={total_pages}"

    @staticmethod
    def convert_pdf_to_jpg(pdf_path, reqid):
        """转换PDF为多页JPG并返回基础URL"""
        try:
            images = convert_from_path(pdf_path, poppler_path=r'D:\Release-24.08.0-0\poppler-24.08.0\Library\bin')
            total_pages = len(images)
            
            # 保存页面并生成URL
            for page_num, image in enumerate(images, start=1):
                filename = f"{reqid}_page{page_num}.jpg"
                output_path = os.path.join(WATCH_FOLDER, filename)
                image.save(output_path, "JPEG", quality=90)
            
            base_url = PDFProcessor.generate_base_url(reqid, total_pages)
            return base_url, total_pages
        except Exception as e:
            print(f"PDF转换失败: {str(e)}")
            raise

    @staticmethod
    def check_and_process(reqid, recordid, retry_count=0):
        """处理PDF转换流程"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute(""" 
                SELECT reporturl FROM report 
                WHERE reqid = %s AND reporturl IS NOT NULL 
                LIMIT 1
            """, (reqid,))

            if result := cursor.fetchone():
                pdf_types = ['reviewreport', 'anareport']
                
                # 通过文件名判断报告类型
                target_pdf = None
                for report_type in pdf_types:
                    pdf_path = os.path.join(WATCH_FOLDER, f"{recordid}_{report_type}.pdf")
                    if os.path.exists(pdf_path):
                        target_pdf = (pdf_path, report_type)
                        break
                
                if not target_pdf:
                    print(f"未找到有效PDF文件: {recordid}")
                    return

                # 确保传递正确的 report_type 参数
                pdf_path, report_type = target_pdf
                base_url, total_pages = PDFProcessor.convert_pdf_to_jpg(pdf_path, reqid)
                
                cursor.execute(""" 
                    UPDATE report SET 
                        jpgurl = %s,
                        totalpages = %s,
                        createtime = NOW()
                    WHERE reqid = %s
                """, (base_url, total_pages, reqid))
                print(f"成功处理: {recordid}")
                
            else:
                if retry_count < MAX_RETRIES:
                    threading.Timer(RETRY_INTERVAL, PDFProcessor.check_and_process, 
                                  args=(reqid, recordid, retry_count+1)).start()
                else:
                    print(f"达到最大重试次数: {recordid}")
                    
        except mysql.connector.Error as e:
            print(f"数据库错误: {str(e)}")
        except Exception as e:
            print(f"处理异常: {str(e)}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @staticmethod
    def handle_update(reqid):
        """处理报告更新"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            # 获取关联的recordid
            cursor.execute(""" 
                SELECT p.recordid 
                FROM patient p
                JOIN report r ON p.reqid = r.reqid
                WHERE p.reqid = %s
            """, (reqid,))
            record_info = cursor.fetchone()
            
            if not record_info:
                print(f"未找到reqid对应的记录: {reqid}")
                return

            recordid = record_info['recordid']
            
            # 根据文件名来判断报告类型
            pdf_types = ['reviewreport', 'anareport']
            target_pdf = None
            for report_type in pdf_types:
                pdf_path = os.path.join(WATCH_FOLDER, f"{recordid}_{report_type}.pdf")
                if os.path.exists(pdf_path):
                    target_pdf = (pdf_path, report_type)
                    break
            
            if not target_pdf:
                print(f"未找到有效PDF文件: {recordid}")
                return

            # 修复: 确保传递正确的 report_type 参数
            pdf_path, report_type = target_pdf
            # 转换并获取新的图片URL
            base_url, total_pages = PDFProcessor.convert_pdf_to_jpg(pdf_path, reqid)
            
            # 更新数据库
            cursor.execute(""" 
                UPDATE report SET 
                    jpgurl = %s,
                    totalpages = %s,
                    createtime = lastupdate
                WHERE reqid = %s
            """, (base_url, total_pages, reqid))
            conn.commit()
            print(f"成功更新报告: {reqid}")
            
        except Exception as e:
            print(f"更新处理失败: {str(e)}")
            conn.rollback()
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            time.sleep(1)
            self.process_pdf(event.src_path)

    def process_pdf(self, file_path):
        filename = os.path.basename(file_path)
        parts = filename.rsplit('_', 1)
        
        if len(parts) == 2 and parts[1] in ['anareport.pdf', 'reviewreport.pdf']:
            recordid = parts[0]
            self.start_processing(recordid)

    def start_processing(self, recordid):
        """启动后台处理线程"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT reqid FROM patient WHERE recordid = %s", (recordid,))
            if (reqid := cursor.fetchone()[0]):
                threading.Thread(
                    target=PDFProcessor.check_and_process,
                    args=(reqid, recordid)
                ).start()
        except Exception as e:
            print(f"启动处理失败: {str(e)}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

def check_updates():
    """定期检查需要更新的报告"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(""" 
            SELECT reqid 
            FROM report 
            WHERE lastupdate != createtime
            OR createtime IS NULL
        """)
        
        for row in cursor.fetchall():
            reqid = row['reqid']
            print(f"检测到需要更新的报告: {reqid}")
            threading.Thread(target=PDFProcessor.handle_update, args=(reqid,)).start()
            
    except Exception as e:
        print(f"更新检查失败: {str(e)}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/report/jpg')
def serve_report_image():
    """图片服务端点"""
    reqid = request.args.get('reqid')
    page = request.args.get('page', 1, type=int)  # 新增页码参数
    
    if not reqid or page < 1:
        return jsonify({"error": "参数错误"}), 400
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 获取总页数用于验证
        cursor.execute("SELECT totalpages FROM report WHERE reqid = %s", (reqid,))
        if not (report := cursor.fetchone()):
            return jsonify({"error": "未找到对应报告"}), 404
            
        total_pages = report['totalpages']
        if page > total_pages:
            return jsonify({"error": "页码超出范围"}), 400

        # 直接根据reqid和页码构造文件名
        filename = f"{reqid}_page{page}.jpg"
        return send_from_directory(WATCH_FOLDER, filename)
        
    except mysql.connector.Error as e:
        return jsonify({"error": f"数据库错误: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/reports')
def get_report_data():
    """报告数据API"""
    recordid = request.args.get('recordid')
    if not recordid:
        return jsonify({"error": "缺少recordid参数"}), 400
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(""" 
            SELECT p.reqid, r.jpgurl, r.totalpages, r.createtime, r.lastupdate 
            FROM patient p
            JOIN report r ON p.reqid = r.reqid
            WHERE p.recordid = %s
        """, (recordid,))
        
        if not (result := cursor.fetchone()):
            return jsonify({"error": "未找到记录"}), 404
        
        return jsonify({
            "recordid": recordid,
            "reqid": result['reqid'],
            "base_url": result['jpgurl'],
            "totalpages": result['totalpages'],
            "createtime": result['createtime'].isoformat() if result['createtime'] else None,
            "lastupdate": result['lastupdate'].isoformat() if result['lastupdate'] else None
        })
        
    except mysql.connector.Error as e:
        return jsonify({"error": f"数据库错误: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/page-count')
def get_page_count():
    """获取报告总页数"""
    reqid = request.args.get('reqid')
    if not reqid:
        return jsonify({"error": "缺少reqid参数"}), 400
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT totalpages FROM report WHERE reqid = %s", (reqid,))
        if not (result := cursor.fetchone()):
            return jsonify({"error": "未找到记录"}), 404
            
        return jsonify({
            "reqid": reqid,
            "total_pages": result['totalpages']
        })
        
    except mysql.connector.Error as e:
        return jsonify({"error": f"数据库错误: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    try:
        init_database()
        os.makedirs(WATCH_FOLDER, exist_ok=True)

        observer = Observer()
        observer.schedule(PDFHandler(), WATCH_FOLDER, recursive=True)
        observer.start()

        schedule.every(CHECK_INTERVAL).minutes.do(check_updates)

        threading.Thread(target=run_scheduler, daemon=True).start()
        
        app.run(
            host=SERVER_HOST,
            port=SERVER_PORT,
            debug=False,
            use_reloader=False,
            threaded=True
        )

    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.join()
