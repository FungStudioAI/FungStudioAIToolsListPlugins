# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup, Tag

class LoginManager(object):

    def __init__(self,lock,mainwindow,console,asynchSignalManager):
        self.lock = lock
        self.mainwindow = mainwindow
        self.console = console
        self.AsynchSignalManager = asynchSignalManager

    def login(self, session, user, password):
        # 登录URL
        login_url = "http://cas.hnqczy.com:8002/cas/login?service=http%3A%2F%2Fportal.hnqczy.com%2Flogin"
        try:
            self.console.write("正在尝试获取资源锁......", 1)
            with self.lock:
                self.console.write("获取资源锁成功！", 0)
                self.login_stat = False
                self.AsynchSignalManager.call_event_change_signal.emit("logining",(self.login_stat,))      
                # 设置请求头以模仿浏览器
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site'
                }
                self.console.write("正在登进校园网中......", 0)
                # 发送GET请求以获取登录页面
                response = session.get(login_url, headers=headers)
                # 检查请求是否成功
                if response.status_code != 200:
                    self.console.write("校园网服务器响应错误！请重试！", 2)
                    return
                # 解析返回的HTML内容
                soup = BeautifulSoup(response.text, 'html.parser')
                # 查找所有隐藏输入字段
                hidden_inputs = soup.find_all('input', type='hidden')
                form_data = {hidden_input.get('name'): hidden_input.get('value') for hidden_input in hidden_inputs}
                # 添加用户名和密码到表单数据中
                form_data.update({
                    'username': f'{user}',
                    'password': password
                })
                # 发送POST请求进行登录
                response = session.post(login_url, headers=headers, data=form_data, allow_redirects=True)
                if response.status_code != 200:
                    self.console.write("校园网服务器响应错误！请重试！", 2)
                    return
                soup = BeautifulSoup(response.text, 'html.parser')
                div_usr = soup.find_all('div', class_='nameBox')
                if not div_usr:
                    self.console.write("账号密码错误！", 1)
                    return
                self.console.write("校园网登入成功！", 0)
                name = div_usr[0].find('span', class_='name')
                self.AsynchSignalManager.call_uiUpdate_signal.emit("user", (name.get_text(),))
                self.console.write(f"登入者：{name.get_text()}", 0)

                headers.update({
                    'Referer': 'https://v1.chaoxing.com/',  # 根据实际情况调整
                    'Origin': 'https://v1.chaoxing.com'
                })
                # 获取JSESSIONID和其他Cookies
                cookies = {
                    cookie.name: cookie.value for cookie in session.cookies
                }
                self.console.write("正在登进顶岗实习平台中......", 0)
                # 登入顶岗实习平台
                response = session.get("https://v1.chaoxing.com/appInter/openPcApp?mappId=8985934",
                                    cookies=cookies,
                                    headers=headers,
                                    allow_redirects=True)
                if response.status_code != 200:
                    self.console.write("顶岗实习平台服务器响应错误！请重试！", 2)
                    return
                    #获取个人信息
                response = session.get("http://dgsx.hnqczy.com:8090/sys/user/view-me", allow_redirects=True)
                if response.status_code != 200:
                    self.console.write("顶岗实习平台服务器响应错误！请重试！", 2)
                    return
                soup = BeautifulSoup(response.text, 'html.parser')
                div_loginInfo = soup.find_all('div', id='loginName')
                if not div_loginInfo:
                    self.console.write("顶岗实习平台登入失败！请重试！", 2)
                    return
                self.console.write("顶岗实习平台中登入成功！", 0)
                self.console.write(f"顶岗实习平台登入者：{div_loginInfo[0].get_text().strip()}", 0)

                self.console.write("当前顶岗实习学生数据拉取中......", 0)
                # 获取实习班级数据
                response = session.get("http://dgsx.hnqczy.com:8090/homepage/main",
                                    allow_redirects=True)
                if response.status_code != 200:
                    self.console.write("顶岗实习学生数据拉取失败！请重试！", 2)
                    return
                soup = BeautifulSoup(response.text, 'html.parser')
                trs = soup.find_all('tr')
                for tr in trs:
                    ths = tr.find_all('th')
                    tds = tr.find_all('td')
                    if tds:
                        self.console.write(
                            f"所属专业（方向）:{tds[1].get_text()} 班级:{tds[2].get_text()} 课程名称：:{tds[3].get_text()} "
                            f"开始日期：:{tds[4].get_text()} 结束日期：:{tds[5].get_text()} 人数：:{tds[6].get_text()}", 0)
                self.login_stat = True
        except Exception as e:
            self.console.write(f"Exception caught: {e}", 2)
        finally:
            self.AsynchSignalManager.call_event_change_signal.emit("logined",(self.login_stat,))