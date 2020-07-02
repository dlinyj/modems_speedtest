#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import speedtest
from send_email import *
import time
from gps3.agps3threaded import AGPS3mechanism
from datetime import datetime
import threading
import socket
import logging
import traceback

header_csv = "Operator; #Test; Date; Time; Coordinates; Download Mb/s; Upload Mb/s; ping; Testserver\n"
delimiter = ';'
message_log = "Логи тестирования платы №1"

EmailForSend = ["dlinyj@trololo.ru", "pupkin@trololo.ru"]
files = ["/home/khadas/modems_speedtest/csv"]

time_send_csv = ('00:00','06:00','12:00','18:00')
ready_to_send = False
error_list = []
error_status = False


def cmd_run(cmd):
	print(cmd)
	os.system(cmd)

#sheduler
def ShedulerThread(name):
	global ready_to_send
	while True:
		d = datetime.today()
		time_x = d.strftime('%H:%M')
		if time_x in time_send_csv:
			ready_to_send = True
		if error_status:
			error_blink()
		else:
			good_blink()
		time.sleep(1)

#gpio subsistem
def gpio_init():
	os.system("gpio -g mode 421 out")
	os.system("gpio -g write 421 1")

def gpio_set(val):
	os.system("gpio -g write 421 %d" % val)
	
def error_blink():
	gpio_set(0)
	time.sleep(0.1)
	gpio_set(1)
	time.sleep(0.1)
	gpio_set(0)
	time.sleep(0.1)
	gpio_set(1)
	time.sleep(0.1)
	gpio_set(0)
	time.sleep(1.0)
	gpio_set(1)

def good_blink():
	gpio_set(1)

def internet(host="ya.ru", port=80, timeout=3):
	try:
		socket.setdefaulttimeout(timeout)
		socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
		print("Internet test True")
		return True
	except socket.error as ex:
		print(ex)
		print("Internet test False")
		return False

def pingtest(hostname = "google.com"):
	response = os.system("ping -c 1 " + hostname + " > /dev/null  2>&1")
	if response == 0:
		print("Ping test True")
		return True
	else:
		print("Ping test False")
		return False

def NetworkAvalible():
	#return internet() and pingtest()
	return pingtest()

def sendLogs():
	global EmailForSend
	curdata = datetime.now().strftime('%d.%m.%Y')
	сurtime = datetime.now().strftime('%H:%M:%S')
	try:
		for addr_to in EmailForSend:
			send_email(addr_to, message_log, "Логи за " + curdata + " " + сurtime, files)
	except:
		print("Network problem for send mail")
		return False
	return True

def SendErrors():
	global error_list
	global error_status
	print ("Send all errors")
	print ("=====================================================================")
	print ("Error list =\n" + "\n".join(error_list))
	print ("=========================END=========================================")
	mess= "\n".join(error_list)
	filellist = []
	os.system('echo "'+ '\n'.join(error_list) + '" >> csv/error.log')
	os.system('echo "'+ '\n'.join(error_list) + '" | ssh vimssh@host.com  -T "cat >> /home/vimssh/error.log"')
	
	error_list.clear()
	error_status = False
	return True
		

def ErrorMessage(Error_mes):
	global error_list
	global error_status
	error_status = True
	curdata = datetime.now().strftime('%d.%m.%Y')
	сurtime = datetime.now().strftime('%H:%M:%S')
	print(Error_mes)
	error_list.append(curdata + " " + сurtime + " " + Error_mes)
	

def getPositionData(agps_thread):
	counter = 0;
	while True:
		longitude = agps_thread.data_stream.lon
		latitude = agps_thread.data_stream.lat
		if latitude != 'n/a' and longitude != 'n/a':
			return '{}' .format(longitude), '{}' .format(latitude)
		counter = counter + 1
		print ("Wait gps counter = %d" % counter)
		if counter == 10:
			ErrorMessage("Ошибка GPS приёмника!!!")
			return "NA", "NA"
		time.sleep(1.0)


def getNetworklist():
	full_networklist = os.listdir('/sys/class/net/')
	network_list = [x for x in full_networklist if "eth" in x and x != "eth0"]
	return network_list

def SetIpAllNetwork(network_list):
	for iface in network_list:
		lastip = "%d" % (3 + network_list.index(iface))
		cmd_run ("sudo ifconfig " + iface + " 192.168.8." + lastip +" up")

def InitRouteForSSH():
	cmd_run("sudo iptables -t mangle -A OUTPUT -p tcp -m tcp --dport 22 -j MARK --set-mark 0x2")
	cmd_run("sudo ip rule add fwmark 0x2/0x2 lookup 102")

def SetupReverseSSH(iface):
	cmd_run("sudo systemctl stop autossh.service")
	cmd_run("sudo ip route add default via 192.168.8.1 dev " + iface +" table 102")
	cmd_run("sudo systemctl start autossh.service")
	
	
def ConfigNetwork(iface):
		cmd_run("sudo ip route flush all")
		cmd_run("sudo route add default gw 192.168.8.1 " + iface)
		time.sleep(4)

		cmd_run ("sudo bash -c 'echo nameserver 8.8.8.8 > /etc/resolv.conf'")

def count_lines(filename, chunk_size=1<<13):
	try:
		with open(filename) as file:
			return sum(chunk.count('\n')
				for chunk in iter(lambda: file.read(chunk_size), ''))
	except IOError:
		print(traceback.format_exc())
		print("An IOError has occurred!")
		ErrorMessage("count_lines An IOError has occurred!")
		return 0

if __name__ == '__main__':
	format = "%(asctime)s: %(message)s"
	#logging.basicConfig(format=format, level=logging.INFO,
	#					datefmt="%H:%M:%S")

	#gps
	agps_thread = AGPS3mechanism()  # Instantiate AGPS3 Mechanisms
	agps_thread.stream_data()  # From localhost (), or other hosts, by example, (host='gps.ddns.net')
	agps_thread.run_thread()  # Throttle time to sleep after an empty lookup, default '()' 0.2 two tenths of a second
	
	
	#Sheduler branch
	pShedulerThread = threading.Thread(target=ShedulerThread, args=(1,))
	pShedulerThread.start()
	running = True
	
	gpio_init()
	operator_name = []
	
	session_counter = 0
	old_network_list = []
	ercounter = [] #Счётчик ошибок по интерфейсам
	
	InitRouteForSSH()
	lastbanint = "free"
	sshint = "free"
	try:
		print("Application started!")
		while running:
			network_list = getNetworklist()
			if old_network_list != network_list:
				if session_counter == 0:
					print ("First run")
				else:
					ErrorMessage("*****************************\n" +
						"Change network configuration!!!!\n" +
						"*****************************")
				operator_name.clear()
				ercounter.clear()
				for i in range(len(network_list)):
					operator_name.append("NA")
					ercounter.append(0)
				old_network_list = network_list
				SetIpAllNetwork(network_list)
			print("*** Interfaces and network errors")
			print(network_list)
			print(ercounter)
			if network_list:
				for iface in network_list:
					try:
						ConfigNetwork(iface)
						if not NetworkAvalible():
							#Считаем ошибки на интерфейсе
							ercounter[network_list.index(iface)] = ercounter[network_list.index(iface)] + 1
							str_ercounter = list(map(str, ercounter))
							ErrorMessage("Network unavailable on the "+ iface + 
								"\nlist ifaces:\n" + "\t".join(network_list) + 
								"\non OPOS\n" + "\t".join(operator_name) + 
								"\nError count of interfaces:\n" + "\t".join(str_ercounter) +
								"\nSession Counter = " + str(session_counter))
							#сохраняем последний бедовый интерфейс
							lastbanint = iface
						else: #Есть сеть, ура, работаем!
							#Если у нас проблемный интерфейс, на котором ssh, то меняем его
							if (sshint == lastbanint or sshint =="free"):
								print("********** Setup SSH ********************")
								if sshint !="free":
									cmd_run("sudo ip route del default via 192.168.8.1 dev " + sshint +" table 102")
								SetupReverseSSH(iface)
								sshint = iface
							#раз сетка работает, то давай срочно всё отправим!!!
							if ready_to_send:
								print ("**** Ready to send!!!")
								if sendLogs():
									ready_to_send = False
								if error_status:
									SendErrors()
							if (error_status):
								SendErrors()

							#здесь добавить сервера!
							#servers = []
							#6053) MaximaTelecom (Moscow, Russian Federation) [0.12 km]
							servers = ["6053"]
							threads = None
							# If you want to use a single threaded test
							# threads = 1
							s = speedtest.Speedtest()
							opos = '%(isp)s' % s.config['client']
							operator_name[network_list.index(iface)] = opos
							#проверяем существование файла opos.csv, если есть считаем количество строк-1
							#если нет, делаем шапку
							filename = "/home/khadas/modems_speedtest/csv/" + opos.replace(' ', '_') + ".csv"
							print("Result filename = " + filename)
							if os.path.exists(filename):
								curpos = count_lines(filename) - 1
							else:
								curpos = 0
								print("New file")
								with open(filename, "w") as file:
									file.write(header_csv)
									print(header_csv)
							#дальше тестируем
							s.get_servers(servers)
							s.get_best_server()
							testserver = '%(sponsor)s (%(name)s) [%(d)0.2f km]: %(latency)s ms' % s.results.server
							s.download(threads=threads)
							s.upload(threads=threads)
							s.results.share()

							try:
								longitude, latitude = getPositionData(agps_thread)
								curdata = datetime.now().strftime('%d.%m.%Y')
								curtime = datetime.now().strftime('%H:%M:%S')
								result_string = opos + delimiter + str(curpos) + delimiter + \
									curdata + delimiter + curtime + delimiter + longitude + ', ' + latitude + delimiter + \
									str(s.results.download / 1000.0 / 1000.0) + delimiter + str(s.results.upload / 1000.0 / 1000.0) + \
									delimiter + str(s.results.ping) + delimiter + testserver + "\n"
								with open(filename, "a") as file:
									file.write(result_string)
									print(result_string)
							except:
								ErrorMessage(traceback.format_exc() + "\nProblem save data")
					except (KeyboardInterrupt):
						print(traceback.format_exc())
						raise
					except:
						ErrorMessage(traceback.format_exc() + "\nnetwork problem on iface=" + iface)
			session_counter = session_counter + 1
	#Здесь тестируем, что мы в заданном диапазоне времени и слипимся на десять минут, чтобы работал ssh. Хотя проще делать ежеминутный слип.
	except (KeyboardInterrupt):
		print(traceback.format_exc())
		running = False
		print("Applications closed!")
		exit(0)
