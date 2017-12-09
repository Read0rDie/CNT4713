import socket
import threading
import sys
import getpass
import string
import json
import select
from tkinter import *
from multiprocessing import Queue
from time import sleep
from tkinter.font import Font



INVALID_USER = '!524#&^*)-=37_=`*'

PRIVATE_MESSAGE = 1
PUBLIC_MESSAGE = 2
CHANGE_CHANNEL = 3
LOGIN = 4
LEAVE_CHANNEL = 5
JOIN_CHANNEL = 6
CREATE_CHANNEL = 7

def auth():
    username = input('Username: ')
    password = getpass.getpass('Password: ')
    return username, password

class ChatServer:    
    
    commands = [':/exit' , ':/logout']
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connections = {}
    channels = {'General' : [], 'Noob' : [], 'Beginner' : [], 'Intermediate' : [], 'Advanced' : [], 'Expert' : []}
    users = {}
    user_to_conn = {}
    valid_users = {'alex' : 'alex', 'mark' : 'mark', 'juan' :  'juan'}
    if(len(sys.argv) == 2):
        print('You have joined the CNT-4713 chat server. Please authenticate yourself')
    if(len(sys.argv) == 1):
        print('Server initilaized...')

    def __init__(self):
        self.server_buffer = []
        self.sock.bind(('0.0.0.0', 4713))
        self.sock.listen(5)
        
    def disconnect(self, conn, channel, msg):
        print(msg)        
        name = self.users[conn]
        del self.users[conn]
        del self.connections[conn]
        self.channels[channel].remove(conn)
        
        if not name  == INVALID_USER: 
            for connection in self.channels[channel]:                    
                if conn != connection:                        
                    self.updateBuffer(name + ' has left the chat room...\n', channel)
                    self.setMessageType(LEAVE_CHANNEL)
                    self.sendBuffer(connection)                
        conn.close()

    def client_handler(self, conn, atr):        
        found = False
        auth_data = conn.recv(4096)
        decode = auth_data.decode('utf-8')
        decode = json.loads(decode)        
        channel = 'General'
        
        if decode[0] in self.valid_users:
            if(self.valid_users[decode[0]] == decode[1]):
                found = True
        if(found == False):
            self.invalidateBuffer('invalid')
            self.sendBuffer(conn)
            self.channels['General'].remove(conn)
            del self.connections[conn]
            name = INVALID_USER
            conn.close()           
            
        else:
            self.users[conn] = decode[0]            
            name = self.users[conn]
            self.user_to_conn[name] = conn
            self.updateBuffer('You have successfully logged in...\n', 'General')
            self.setMessageType(CHANGE_CHANNEL)
            self.sendBuffer(conn)
            for connection in self.channels[decode[2]]:                    
                    if conn != connection:                        
                        self.updateBuffer(self.users[conn] + ' has joined the chat room...\n', 'General')
                        self.setMessageType(JOIN_CHANNEL)
                        self.sendBuffer(connection)
        while (True):
            try:
                data = conn.recv(1048)
                reply_buffer = data.decode('utf-8')
                reply_buffer = json.loads(reply_buffer)
                message_type = reply_buffer[0]
                if message_type == CHANGE_CHANNEL:
                    self.updateChannel(conn, reply_buffer[1])
                    self.connections[conn] = reply_buffer[1]
                elif message_type == PRIVATE_MESSAGE:
                    self.privateMsg(reply_buffer, self.user_to_conn[reply_buffer[2]], conn)                  
                elif message_type == PUBLIC_MESSAGE:                    
                    self.publicMsg(reply_buffer, self.users[conn], conn)
                elif message_type == CREATE_CHANNEL:
                    self.channels[reply_buffer[1]] = []
                    self.updateChannel(conn, reply_buffer[1])
                    self.connections[conn] = reply_buffer[1]
                elif message_type == LOGIN:
                    continue
                
            except Exception as e:
                if name != INVALID_USER:                    
                    self.disconnect(conn, self.connections[conn], str(atr[0]) + ':' + str(atr[1]) + ' disconnected')
                    del self.user_to_conn[name]
                else:                    
                    print(str(atr[0]) + ':' + str(atr[1]) + ' disconnected')
                    conn.close()
                break           
            if not data:                
                self.disconnect(conn, self.connections[conn], str(atr[0]) + ':' + str(atr[1]) + ' disconnected')
                break            
    
    def run(self):
        while True:
            conn, atr = self.sock.accept()
            cThread = threading.Thread(target=self.client_handler, args=(conn, atr))
            cThread.daemon = True
            cThread.start()
            self.channels['General'].append(conn)
            self.connections[conn] = 'General'
            print(str(atr[0]) + ':' + str(atr[1]), 'connected')            

    def invalidateBuffer(self, msg):
        self.server_buffer.append(msg)
        user_list = []        
        for key in self.users:
            user_list.append(self.users[key])
        self.server_buffer.append(user_list)

    def updateBuffer(self, msg, channel):
        self.server_buffer.append(msg)
        user_list = []
        channel_list = []
        for conn in self.channels[channel]:
            user_list.append(self.users[conn])
        self.server_buffer.append(user_list)
        for key in self.channels:
            channel_list.append(key)
        self.server_buffer.append(channel_list)

    def sendBuffer(self, conn):
        buffer = self.server_buffer
        conn.send(str.encode(json.dumps(buffer)))        
        self.server_buffer = []

    def updateChannel(self, conn, new_channel):
        channel = self.connections[conn]
        self.channels[self.connections[conn]].remove(conn)
        self.channels[new_channel].append(conn)
        for connection in self.channels[channel]:
            if conn != connection:
                self.updateBuffer(self.users[conn] + ' has left the chat room...\n', channel)
                self.setMessageType(LEAVE_CHANNEL)
                self.sendBuffer(connection)        
        for connection in self.channels[new_channel]:
            if conn != connection:
                self.updateBuffer(self.users[conn] + ' has joined the chat room...\n', new_channel)
                self.setMessageType(JOIN_CHANNEL)
                self.sendBuffer(connection)
            else:
                self.updateBuffer('You have joined the \'' + new_channel + '\' channel...\n', new_channel)
                self.setMessageType(CHANGE_CHANNEL)
                self.sendBuffer(connection)

    def setMessageType(self, message_type):
        self.server_buffer.append(message_type)


    def publicMsg(self, reply_buffer, name, conn):
        reply = '<' + self.users[conn] + '> : ' + reply_buffer[1]
        for connection in self.channels[self.connections[conn]]:                    
                if conn != connection and name != INVALID_USER:                        
                    self.updateBuffer(reply, self.connections[conn])
                    self.setMessageType(PUBLIC_MESSAGE)
                    self.sendBuffer(connection)

    def privateMsg(self, reply_buffer, pconn, conn):
        reply = self.users[conn] + ' whispered ~ ' + reply_buffer[1]
        self.updateBuffer(reply, self.connections[conn])
        self.setMessageType(PRIVATE_MESSAGE)
        self.sendBuffer(pconn)

class ChatClient:    
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def createChannel(self):
        buffer = [CREATE_CHANNEL, self.channel]
        self.sock.send(str.encode(json.dumps(buffer)))
        return 0

    def changeChannel(self):
         buffer = [CHANGE_CHANNEL, self.channel]
         self.sock.send(str.encode(json.dumps(buffer)))

    def login(self):
        login_buffer = [LOGIN, self.username, self.password]
        self.sock.send(str.encode(json.dumps(login_buffer)))

    def publicMsg(self, mesg):
        public_buffer = [PUBLIC_MESSAGE, mesg]
        self.sock.send(str.encode(json.dumps(public_buffer)))
        
    def privateMsg(self, mesg, dest):
        private_buffer = [PRIVATE_MESSAGE, mesg, dest]
        self.sock.send(str.encode(json.dumps(private_buffer)))

    def sendMsg(self, mesg):        
        buffer = [mesg, self.channel]
        self.sock.send(str.encode(json.dumps(buffer)))

    def getMsg(self):
        while self.running:
            data = self.sock.recv(4096)
            buffer = data.decode('utf-8')
            try:
                buffer = json.loads(buffer)
            except:
                print()
            self.queue.put(buffer)
        return

    def __init__(self, address, master):
        self.master = master
        self.sock.connect((address, 4713))
        self.queue = Queue()
        client_auth = auth()        
        self.username = client_auth[0]
        self.password = client_auth[1]
        self.running = 1
        self.channel = 'General'

        login_buffer = [self.username, self.password, self.channel]
        self.sock.send(str.encode(json.dumps(login_buffer)))

        data = self.sock.recv(4096)
        verify = data.decode('utf-8')
        verify = json.loads(verify)

        if(verify[0] == 'invalid'):
            print('Invalid Authenication Provided : Connection Terminated')
            self.sock.close()
            quit()
                
        self.app = ChatWindow(self, root)
        self.app.master.title('CNT-4713 Chat Server')
        self.queue.put(verify)                
        
        self.thread1 = threading.Thread(target=self.getMsg)
        self.thread1.daemon = True
        self.thread1.start()
        self.periodicCall()        

    def close(self):
        self.running = 0        

    def periodicCall(self):        
        self.app.checkQueue()
        if not self.running:            
            self.sock.close()
            root.quit()
        self.master.after(200, self.periodicCall)


class ChatWindow(Frame):
        users = {}
        channels = {}        

        def __init__(self, client, master=None):
            root.protocol("WM_DELETE_WINDOW", self.shutdown)
            Frame.__init__(self,master)
            self.queue = client.queue
            self.client = client
            self.master = master
            self.init_components()
            self.has_connection = True
            self.running = client.running
            self.end = client.close
            self.channel = client.channel
            self.user = self.client.username
            self.selectUser = self.client.username
            

        def checkQueue(self):            
            while self.queue.qsize():                
                try:                    
                    self.update()
                except Queue.Empty:                    
                    pass

        def shutdown(self):            
            self.end()

        def getIndex(self):
            index = 0
            temp_list = list(self.channel_list.get(0, END))
            for channel in temp_list:
                if channel == self.channel:
                    return index
                index += 1                

        def update(self):
            buffer = self.queue.get()
            self.updateMsg(buffer[0], buffer[3])
            self.updateUsers(buffer[1])
            self.updateChannels(buffer[2])

        def updateMsg(self, msg, mType):            
            self.msg_list.config(state=NORMAL)
            if(mType == PUBLIC_MESSAGE):
                self.msg_list.insert(END, '  ' + msg.split(' ', 1)[0].strip('\n'), 'public-from')
                self.msg_list.insert(END, msg.split(' ', 1)[1], 'normal')
            else:
                self.msg_list.insert(END, '  ' + msg, self.font_styles[mType])
            self.msg_list.config(state=DISABLED)
            #self.msg_list.see(END)

        def updateUsers(self, users):
            self.user_list.delete(0, END)
            self.user_list.selection_clear(0, self.user_list.size() - 1)
            for user in users:
                self.user_list.insert(END, user)
            self.user_list.see(END)

        def updateChannels(self, channels):
            self.channel_list.delete(0, END)
            self.channel_list.selection_clear(0, self.channel_list.size() - 1)
            for channel in channels:
                self.channel_list.insert(END, channel)
            self.channel_list.select_set(self.getIndex())
            self.channel_list.see(END)
            self.selectUser = self.user;

        def submit(self, event):
            message = self.text1.get(1.0, END)
            self.text1.delete(1.0, END)
            self.client.publicMsg(message)
            self.msg_list.config(state=NORMAL)
            self.msg_list.insert(END, '  <You> : '.strip('\n'), 'public-to')
            self.msg_list.insert(END, message, 'normal')            
            self.msg_list.config(state=DISABLED)
            self.msg_list.yview_moveto(1)

        def privateSubmit(self, event):            
            if not(self.selectUser == self.user):
                dest = self.selectUser
                message = self.private_msg.get(1.0, END)                
                self.private_msg.delete(1.0, END)                
                self.client.privateMsg(message, dest)                
                self.msg_list.config(state=NORMAL)                
                self.msg_list.insert(END, '  You whispered ~\t' + message, "whisper-to")                
                self.msg_list.config(state=DISABLED)
                self.msg_list.yview_moveto(1)                

        def selectChannel(self, evt):
            index_list = self.channel_list.curselection()
            index = index_list[0]
            temp_list = list(self.channel_list.get(0, END))
            self.client.channel = temp_list[index]
            self.channel = temp_list[index]
            self.client.changeChannel()

        def modified(self, event):
            self.txt.see(END)

        def selectUser(self, event):
            widget = event.widget
            selection=widget.curselection()
            self.selectUser = widget.get(selection[0])

        def createChannel(self, event):
            found = False            
            chan = self.create_channel.get()            
            if(len(chan) > 0):                
                for channel in list(self.channel_list.get(0, END)):
                    if channel == chan:
                        print(chan)
                        found = True
                if not found:
                    self.client.channel = chan
                    self.channel = chan
                    self.client.createChannel()          

        def init_fonts(self):
            self.boldslant = Font(family="Helvetica", size=9, weight="bold", slant='italic')
            self.slant = Font(family="Helvetica", size=9, slant='italic')
            self.normal = Font(family="Helvetica", size=9, weight="normal")
            self.bold = Font(family="Helvetica", size=10, weight="bold")

            self.msg_list.tag_configure('private', font=self.boldslant, foreground='DodgerBlue3')
            self.msg_list.tag_configure('whisper-to', font=self.boldslant, foreground='DodgerBlue3')
            self.msg_list.tag_configure('public', font=self.bold, foreground='DodgerBlue3')
            self.msg_list.tag_configure('public-to', font=self.bold, foreground='DodgerBlue3')
            self.msg_list.tag_configure('public-from', font=self.bold, foreground='DarkOrange1')
            self.msg_list.tag_configure('change', font=self.bold, foreground='lightseagreen')
            self.msg_list.tag_configure('join', font=self.bold, foreground='lightseagreen')
            self.msg_list.tag_configure('leave', font=self.bold, foreground='firebrick3')
            self.msg_list.tag_configure('normal', font=self.bold)

            self.font_styles = {}
            self.font_styles[PUBLIC_MESSAGE] = 'normal'
            self.font_styles[PRIVATE_MESSAGE] = 'private'
            self.font_styles[CHANGE_CHANNEL] = 'change'
            self.font_styles[JOIN_CHANNEL] = 'join'
            self.font_styles[LEAVE_CHANNEL] = 'leave'
      
        def init_components(self):
            message_frame = Frame(self.master, bg='DarkOrchid4', width=400, height=250, pady=3, padx=3)
            type_frame = Frame(self.master, bg='DarkOrchid4', width=400, height=150, padx=3, pady=3)
            channel_frame = Frame(self.master, bg='DarkGoldenrod1', width=200, height=45, pady=3)
            user_frame = Frame(self.master, bg='DarkOliveGreen3', width=200, height=60, pady=3)

            self.master.grid_rowconfigure(1, weight=1)
            self.master.grid_columnconfigure(0, weight=1)
            self.master.grid_columnconfigure(2, minsize=200)
            self.master.grid_columnconfigure(1, minsize=200)
            self.master.grid_rowconfigure(0, minsize=250)
            

            message_frame.grid(row=0, column=0,sticky="nsew")
            type_frame.grid(row=1, column=0, sticky="nsew")
            channel_frame.grid(row=0, column=1, sticky="nsew", rowspan=2)
            user_frame.grid(row=0, column=2, sticky="nsew", rowspan=2)

            chat_lbl = Label(message_frame, bg='DarkOrchid4', fg='white', text="CNT-4713 Chat Room", font='papyrus 13 bold')
            chat_lbl.pack(side=TOP, pady=2)

            listbox1 = Text(message_frame, width=400, height=1, wrap=WORD)
            
            scrollbar = Scrollbar(message_frame)            
            scrollbar.pack(side=RIGHT, fill=Y, in_=listbox1)
            
            listbox1.pack(side=TOP, fill=BOTH, padx=5, pady=2, expand=True)
            listbox1.config(state=DISABLED)
            
            listbox1.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=listbox1.yview)
            
            text1 = Text(type_frame, width=400, height=4)
            text1.pack(side=TOP, fill=BOTH, padx=5, pady=(2,5), expand=True)            

            enterButton = Button(type_frame, text="Enter")
            enterButton.pack(side=RIGHT, padx=5, pady=2)

            clearButton = Button(type_frame, text="Clear")
            clearButton.pack(side=RIGHT, padx=4, pady=2)

            channel_lbl = Label(channel_frame, bg='DarkGoldenrod1', text="Channels", font='papyrus 13 bold')
            channel_lbl.pack(side=TOP, pady=2)

            listbox2 = Listbox(channel_frame, width=30, height=15, exportselection=0)

            channelbar = Scrollbar(channel_frame)            
            channelbar.pack(side=RIGHT, fill=Y, in_=listbox2)
            
            listbox2.pack(side=TOP, fill=BOTH, padx=5, pady=2, expand=True)

            listbox2.config(yscrollcommand=channelbar.set)
            channelbar.config(command=listbox2.yview)

            enterChannel = Button(channel_frame, text="Create")
            enterChannel.pack(side=RIGHT, padx=5, pady=2)

            channelEntry = Entry(channel_frame)
            channelEntry.pack(side=TOP, fill=X, padx=(5,0), pady=(4,2))

            user_lbl = Label(user_frame, bg='DarkOliveGreen3', text="Users", font='papyrus 13 bold')
            user_lbl.pack(side=TOP, pady=2)
            
            listbox3 = Listbox(user_frame, width=30, height=15, exportselection=0)

            userbar = Scrollbar(user_frame)            
            userbar.pack(side=RIGHT, fill=Y, in_=listbox3)

            listbox3.pack(side=TOP, padx=5, fill=BOTH, pady=2, expand=True)

            listbox3.config(yscrollcommand=userbar.set)
            userbar.config(command=listbox3.yview)
                                                    
            userEntry = Text(user_frame, width=23, height=4)
            userEntry.pack(side=TOP, padx=5, pady=(5,4))

            whisperUser = Button(user_frame, text="Message User")
            whisperUser.pack(side=RIGHT, padx=5, pady=2)            

            enterButton.bind('<Button-1>', self.submit)
            whisperUser.bind('<Button-1>', self.privateSubmit)
            enterChannel.bind('<Button-1>', self.createChannel)
            listbox2.bind('<<ListboxSelect>>', self.selectChannel)
            listbox3.bind('<<ListboxSelect>>', self.selectUser)

            self.text1 = text1
            self.msg_list = listbox1
            self.user_list = listbox3
            self.channel_list = listbox2;
            self.channel_list.select_set(0)
            self.private_msg = userEntry
            self.create_channel = channelEntry;

            self.init_fonts()

                           
if(len(sys.argv)> 1):
    root = Tk()
    root.geometry("800x400")
    root.resizable(False, False)
    client = ChatClient(sys.argv[1], root)   
    root.mainloop()
else:
    server = ChatServer()
    server.run()

