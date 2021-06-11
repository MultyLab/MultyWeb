# Project Name : micropython-MultyWeb
# File Name : MultyWeb
#-*-coding:utf-8-*-
# Creat Time : 2021/4/1 19:57
# Creator : MultyLab
# Depend on : ESP32+micropython+threading
import json
from lib import threading
import socket
import gc


class request :
    def __init__(self):
        '''
        request object.
        :param path: requese url.
        :param method: request method.
        :param head: request head.
        :param body: request body.
        '''
        self.method = None
        self.path = None
        self.version = None
        self.head = None
        self.body = None

    def procParams(self):
        '''
        procerss request params [GET] [POST]
        :return: request params peocess resoult.
        '''
        if self.method == "POST" :
            params = self.body.decode().split("&")
        elif self.method == "GET" :
            params = self.path.split("?")
        else:
            params = []
        params_res = {}
        for i in params:
            spl = i.split("=")
            if len(spl) == 2:
                params_res[spl[0]] = spl[1]
        return params_res

class MultyWeb:
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'

    # response code.
    OK = b"200 OK"
    NOT_FOUND = b"404 Not Found"
    FOUND = b"302 Found"
    FORBIDDEN = b"403 Forbidden"
    BAD_REQUEST = b"400 Bad Request"
    ERROR = b"500 Internal Server Error"

    # File extension:Content
    MIME_TYPES = {
        'css': 'text/css',
        'html': 'text/html',
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'js': 'text/javascript',
        'json': 'application/json',
        'rtf': 'application/rtf',
        'svg': 'image/svg+xml',
        'ico':'application/ico',
        'bin':"file/bin"
    }

    # File not allowed [example]
    BLACK_LIST = [
        "boot.py",
        "main.py"
    ]

    # Directory not allowed [example]
    BLACK_DIR = [
        "python",
    ]
    # response file [500] [404]
    RESP_FILE = {
        ERROR:"html/500.html",
        NOT_FOUND:"html/404.html"
    }

    def __init__(self, address, port):
        '''
        initialization
        :param address: web server ip address.
        :param port: web server port.
        '''
        self.address = address
        self.port = port
        self.debug = False
        self.routes_dict = {}
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.bind((address,port))
        self.sock.listen(10)
        self.th_server = threading.Thread(target=self.__server)


    #BACKEND SERVER METHODS
    def setRoutes(self, routes={}):
        '''
        Set url resolution table
        :param routes: resolution table
        :return:None
        Look for self.addRoiters().
        '''
        self.routes_dict = routes

    def addRouters(self,routers:dict={}):
        '''
        add url routers.
        :param routers:
        :return:None
        [example]
        X.addRouters({"/":index,})
        # the X is MultyWeb object.
        # the "/" is suburl.
        # the index is process function.
        '''
        self.routes_dict.update(routers)

    def start(self):
        '''
        start server thread.
        :return: None
        '''
        print("Web Service run {} {}".format(self.address,self.port))
        self.th_server.start()


    def __server(self):
        while True :
            cli,addr = self.sock.accept()
            gc.collect()
            threading.Thread(target=self.__router, args=(cli,)).start()
        pass

    def __router(self,client):
        gc.collect()
        recv = client.recv(1024)
        req = self.__processRequest(recv,client)  # type:request
        if req == None :
            return
        print("[{}] : {}".format(req.method,req.path))
        if req.method != None :
            reqpath = req.path.split("?")[0]
            if reqpath in self.routes_dict.keys():
                self.routes_dict[reqpath](req,client)
            else:
                self.sendFile(client,filename=reqpath[1:])
        else:
            pass
            self.render(client, html_file=self.RESP_FILE[self.ERROR], status=self.ERROR)
        gc.collect()
        pass


    def __processRequest(self,reqdata,client) -> request:
        '''
        process response.
        :param reqdata: request data.
        :param client : client socket.
        :return: request object.
        '''
        try :
            request_line, rest_of_request = reqdata.split(b'\r\n', 1)
            request_line = request_line.decode().strip().split(' ')
            req = request()
            if len(request_line) > 1:
                req.method = request_line[0]
                req.path = request_line[1]
                req.version = request_line[2]
            req.head = {}
            raw_headers, body = rest_of_request.split(b'\r\n\r\n', 1)
            raw_headers = raw_headers.split(b'\r\n')
            for header in raw_headers:
                split_header = header.decode().strip().split(': ')
                req.head[split_header[0]] = split_header[1]
            req.body = body
            return req
        except ValueError :
            self.render(client,self.NOT_FOUND,status=self.NOT_FOUND)
            return None


    def sendStatus(self,client,status_code:bytes):
        '''
        send Http response status code.
        :param client: client socket.
        :param status_code: status code.
        :return:
        '''
        response_line = b"HTTP/1.1 "
        client.send(response_line + status_code + b'\n')

    def sendHeaders(self,client,headers_dict:dict={}):
        '''
        send Http response head.
        :param client : client socket.
        :param headers_dict: response head data.
        :return:
        '''
        for key, value in headers_dict.items():
            client.send(b"%s: %s\n" % (key.encode(), value.encode()))

    def sendBody(self,client,body_content):
        '''
        send Http response Body.
        :param client : client socket.
        :param body_content:
        :return:
        '''
        client.send(b'\n' + body_content + b'\n\n')
        client.close()

    def sendOK(self,client):
        '''
        send success code.
        :param client:
        :return:
        '''
        self.sendStatus(client,self.OK)
        self.sendHeaders(client)
        self.sendBody(client,b"")



    def render(self,client,html_file,variables=False, status=OK):
        '''
        Template rendering
        :param client: client socket.
        :param html_file: Template file path.
        :param variables: variables.
        :param status: status code.
        :return: None
        '''
        try:
            self.sendStatus(client,status_code=status)
            self.sendHeaders(client,headers_dict={'Content-Type': 'text/html'})
            client.send(b'\n')
            with open(html_file,'rb') as f:
                for line in f :
                    if variables:
                        for var_name, value in variables.items():
                            line = line.replace(b"{{%s}}" % var_name.encode(), str(value).encode())
                    client.send(line)
            client.send(b"\n\n")
        except Exception as e:
            pass
        client.close()



    def sendJSON(self,client,jsonobj):
        '''
        # send JSON data to client.
        :param client: client object.
        :param jsonobj: python object.
        :return:
        '''
        self.sendStatus(client,status_code=self.OK)
        self.sendHeaders(client,headers_dict={'Content-Type': 'application/json'})
        self.sendBody(client,body_content=json.dumps(jsonobj))
        pass

    def sendFile(self,client,filename):
        '''
        send file .
        :param filename: file path.
        :return:None
        '''
        fsplit = filename.split(".")
        fsplen = len(fsplit)
        if fsplen == 1 :
            extension = "bin"
        else:
            extension = fsplit[-1]
        try:
            if filename in self.BLACK_LIST :
                raise IOError("Permision denide !")
            if "/" in filename :
                dir = filename.split("/")[0]
                if dir in self.BLACK_DIR :
                    raise IOError("Permision denide !")
            with open(filename, 'rb') as f:
                self.sendStatus(client,status_code=self.OK)
                if extension in self.MIME_TYPES.keys():
                    self.sendHeaders(client,headers_dict={'Content-Type': self.MIME_TYPES[extension]})
                else:
                    self.sendHeaders(client, headers_dict={'Content-Type': "application/file"})
                client.send(b"\n")
                while True :
                    gc.collect()
                    buff = f.read(1024)
                    if not buff:
                        f.close()
                        break
                    else:
                        client.send(buff)
            client.send(b"\n\n")
            client.close()
        except Exception as e:
            self.render(client, html_file=self.RESP_FILE[self.NOT_FOUND],status=self.NOT_FOUND)





#     ============================================================
#     Built-in interface

    def addRouter_update(self):
        '''
        Add file update interface to url routing table.
        :return: None
        '''
        self.addRouters({"/update":self.www_update_file})
        pass

    def www_update_file(self,req: request,client):
        '''
        File update interface
        :param req: request object
        :param client: client socket.
        :return: None
        '''
        params = req.procParams()
        if req.method == 'GET':
            if "update" in params.keys():
                path = params["update"]
                path = path.replace("%2F","/")
                print("[ www update ] update file " + path)
                try:
                    res = req.body
                    f = open(path, "wb")
                    if b"#fileend#" in res:
                        print("[ www update] update {} success".format(path))
                        res = res.replace(b"#fileend#", b"")
                        f.write(res)
                        f.close()
                        self.sendStatus(client, status_code=self.OK)
                        self.sendHeaders(client)
                        self.sendBody(client, b"")
                        client.close()
                        return
                    else:
                        f.write(res)
                    while True:
                        gc.collect()
                        res =  client.recv(8192)
                        if b"#fileend#" in res:
                            print("[ www update] update {} success".format(path))
                            res = res.replace(b"#fileend#", b"")
                            f.write(res)
                            f.close()
                            self.sendStatus(client, status_code=self.OK)
                            self.sendHeaders(client)
                            self.sendBody(client,b"")
                            client.close()
                            return
                        elif not res:
                            f.close()
                            self.sendStatus(client, status_code=self.OK)
                            self.sendHeaders(client)
                            self.sendBody(client, b"")
                            client.close()
                            return
                        else:
                            f.write(res)

                except Exception as e:
                    print("{}".format(e))
                    self.render(client, html_file=self.RESP_FILE[self.ERROR], status=self.ERROR)
            else :
                self.render(client, html_file=self.RESP_FILE[self.ERROR], status=self.ERROR)
        else:
            self.render(client, html_file=self.RESP_FILE[self.ERROR], status=self.ERROR)
        pass
#     ================================================================

