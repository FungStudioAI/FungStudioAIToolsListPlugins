import json
from bs4 import BeautifulSoup, Tag

class WeekReportManager():
    def __init__(self,console,lock,asynchSignalManager):
        self.lock = lock
        self.console = console
        self.AsynchSignalManager = asynchSignalManager
    def weekpaperReviewSubmit(self, session, id, msg, name):
        try:
            self.console.write("正在尝试获取资源锁......", 1)
            with self.lock:
                self.console.write("获取资源锁成功！", 0)
                if msg[0] == '':
                    self.console.write("请填写评语！", 1)
                    return
                self.console.write(f"{name} {id} 正在提交评价中......", 0)
                weekpaper_form_data = {
                    "id": id,
                    "evalComment": msg[0],
                    "evalLevel": msg[1]
                }
                # 获取实习班级数据
                response = session.post("http://dgsx.hnqczy.com:8090/process/weekly-report/eval",
                                        data=weekpaper_form_data,
                                        allow_redirects=True)
                if response.status_code != 200:
                    self.console.write(f"{name} {id} 周报评价失败！请重试！", 2)
                    return
                self.console.write(f"{name} {id} 周报评价成功！", 0)
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)

    def weekpaperRedo(self, session, id, name):
        try:
            self.console.write("正在尝试获取资源锁......", 1)
            with self.lock:
                self.console.write("获取资源锁成功！", 0)
                
                self.console.write(f"{name} {id} 正在发回重写中......", 0)
                weekpaper_form_data = {
                    "id": id,
                }
                # 获取实习班级数据
                response = session.post("http://dgsx.hnqczy.com:8090/process/weekly-report/updateRewriteState",
                                        data=weekpaper_form_data,
                                        allow_redirects=True)
                if response.status_code != 200:
                    self.console.write(f"{name} {id} 发回重写失败！请重试！", 2)
                    return
                self.console.write(f"{name} {id} 发回重写成功！", 0)
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)

    def pullWeekpaperContent(self,isDownImg ,session, id, name):
        try:
            self.console.write("正在尝试获取资源锁......", 1)
            with self.lock:
                self.console.write("获取资源锁成功！", 0)
                self.console.write(f"{name} {id} 周报内容拉取中......", 0)
                weekpaper_form_data = {
                    "id": id,
                }
                # 获取实习班级数据
                response = session.post("http://dgsx.hnqczy.com:8090/process/weekly-report/eval-edit",
                                        data=weekpaper_form_data,
                                        allow_redirects=True)
                if response.status_code != 200:
                    self.console.write(f"{name} {id} 周报内容拉取失败！请重试！", 2)
                    return
                self.console.write(f"{name} {id} 周报内容拉取成功！", 0)
                soup = BeautifulSoup(response.text, 'html.parser')
                tds = soup.find_all("td")
                data = (str(tds[3].get_text()).strip(), str(tds[4].get_text()).strip(), str(tds[5].get_text()).strip(),
                        str(tds[6].get_text()).strip(), str(tds[7].find("input").get("value")).strip(),
                        str(tds[8].get_text()).strip())
                self.AsynchSignalManager.call_uiUpdate_signal.emit("weekpaper_content", data)
                if isDownImg:
                    self.console.write(f"{name} {id} 周报图片拉取中......", 0)
                    weekpaper_form_data = {
                        "type":"PROCESS_WEEKLY_REPORT",
                        "rowId":id,
                        "graDocType":"0"
                    }
                    response = session.post("http://dgsx.hnqczy.com:8090/sys/attach/findAttachments",
                                            data=weekpaper_form_data,
                                            allow_redirects=True)
                    if response.status_code != 200:
                        self.console.write(f"{name} {id} 周报图片拉取失败！请重试！", 2)
                        return
                    self.console.write(f"{name} {id} 周报图片拉取成功！", 0)
                    if str(response.text).strip() != '':
                        # 解析JSON数据
                        json_data = json.loads(response.text)
                        if json_data:
                            img_paths = tuple(data['path'] for data in json_data)
                            self.AsynchSignalManager.call_uiUpdate_signal.emit("weekpaper_img", img_paths)
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)

    def pullWeekpapers(self, session, itnspid, stdid, name):
        try:
            self.console.write("正在尝试获取资源锁......", 1)
            with self.lock:
                self.console.write("获取资源锁成功！", 0)
                self.console.write(f"{name} 周报拉取中......", 0)
                weekpaper_form_data = {
                    "internshipId": itnspid,
                    "studentId": stdid
                }
                # 获取实习班级数据
                response = session.post("http://dgsx.hnqczy.com:8090/process/weekly-report/eval-detail",
                                        data=weekpaper_form_data,
                                        allow_redirects=True)
                if response.status_code != 200:
                    self.console.write(f"{name} 周报拉取失败！请重试！", 2)
                    return
                self.console.write(f"{name} 周报拉取成功！", 0)
                soup = BeautifulSoup(response.text, 'html.parser')
                tbody = soup.find_all("tbody")
                trs = tbody[0].find_all("tr")
                self.AsynchSignalManager.call_uiUpdate_signal.emit("reset_wkpr_table", (0,))
                for tr in trs:
                    tds = tr.find_all("td")
                    id = tr.get("id")
                    submit_time = str(tds[2].get_text()).strip()
                    review_time = str(tds[3].get_text()).strip()
                    grade = str(tds[4].get_text()).strip()
                    data = (submit_time, review_time, grade, id)
                    self.AsynchSignalManager.call_uiUpdate_signal.emit("weekpapers", data)
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)

    def pullStudents(self, session, year):
        try:
            self.console.write("正在尝试获取资源锁......", 1)
            with self.lock:
                self.console.write("获取资源锁成功！", 0)
                self.AsynchSignalManager.call_event_change_signal.emit("pulling",(False,))
                weekpaper_form_data = {
                    "conds[grade]": str(year),
                    "conds[semester]": "",
                    "orderCol": "clazz,stu_number",
                    "orderDir": "asc",
                    "limit": "100"
                }
                self.console.write(f"{year}年 顶岗实习学生周报拉取中......", 0)
                # 获取实习班级数据
                response = session.post("http://dgsx.hnqczy.com:8090/process/weekly-report/eval-list",
                                        data=weekpaper_form_data,
                                        allow_redirects=True)
                if response.status_code != 200:
                    self.console.write("顶岗实习学生周报拉取失败！请重试！", 2)
                    self.console.write(f"{response.text}", 2)
                    return
                soup = BeautifulSoup(response.text, 'html.parser')
                tbody = soup.find_all('tbody')
                trs = tbody[0].find_all("tr")
                for tr in trs:
                    internshipid = tr.get("internshipid")
                    studentid = tr.get("studentid")
                    tds = tr.find_all("td")
                    id = tds[2].get_text()
                    name = tds[3].find("a").get_text()
                    class_ = tds[4].get_text()
                    paper_num = tds[7].get_text()
                    paper_writed = tds[8].get_text()
                    paper_no_review = str(tds[12].get_text()).strip()
                    data = (id, name, class_, paper_num, paper_writed, paper_no_review, internshipid, studentid)
                    self.AsynchSignalManager.call_uiUpdate_signal.emit("students", data)
                self.console.write("顶岗实习学生周报数据拉取成功！", 0)
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)
