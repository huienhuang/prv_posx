import socket
import thread
import select
import cStringIO
import time
import errno
from collections import OrderedDict

class TinyAsyncMsgClient:
	def __init__(self, addr, timeout=20):
		self.timeout = timeout
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.s.connect(addr)
		self.b = cStringIO.StringIO()

	def wait_for_buf(self, min_len):
		b = self.b
		v = b.getvalue()
		if len(v) >= min_len: return True

		n = min_len - len(v)
		s = self.s

		s.settimeout(self.timeout)
		while n > 0:
			d = s.recv(4096)
			if not d:
				s.settimeout(None)
				return False
			b.write(d)
			n -= len(d)
		s.settimeout(None)

		return True

	def recv_packet(self):
		if not self.wait_for_buf(3): return None

		b = self.b
		d = b.getvalue()
		p_len = ord(d[0]) + (ord(d[1]) << 8) + (ord(d[2]) << 16)
		if not self.wait_for_buf(p_len): return None

		d = b.getvalue()
		p = d[3:p_len]
		b.seek(0)
		b.write(d[p_len:])
		b.truncate()

		return p

	def send_packet(self, p):
		p = str(p)
		n = len(p) + 3
		d = chr(n&0xFF) + chr((n>>8)&0xFF) + chr((n>>16)&0xFF) + str(p)

		self.s.sendall(d)


class TinyAsyncMsgServer:
	def __init__(self, addr, idle_timeout=60):
		self.addr = addr
		self.idle_timeout = idle_timeout

	def start_forever(self):
		thread.start_new_thread(self._worker, ())

	#callback, don't block
	def process_request(self, s, p):
		pass

	#atomic operation, threadsafe
	def append_response(self, s, p):
		self._res.append( (s, p) )

	def _worker(self):
		_s = self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		_s.setblocking(0)
		_s.bind(self.addr)
		_s.listen(5)

		self._res = []
		self._sck = {}
		self._rlst = set()
		self._wlst = set()
		self._tol = {}

		self._last_ts = int(time.time())

		self._rlst.add(_s)
		while True:
			rl, wl, xl = select.select(self._rlst, self._wlst, self._rlst, 0.1)
			self._process(rl, wl, xl)

	def _parse_packet(self, l):
		d = l[2].getvalue()
		if len(d) < 3: return
		p_len = ord(d[0]) + (ord(d[1]) << 8) + (ord(d[2]) << 16)
		if len(d) >= p_len:
			p = d[3:p_len]
			l[2].seek(0)
			l[2].write( d[p_len:] )
			l[2].truncate()

			self.process_request(l[1], p)

	def _build_packet(self, p):
		p = str(p)
		n = len(p) + 3
		return chr(n&0xFF) + chr((n>>8)&0xFF) + chr((n>>16)&0xFF) + str(p) 

	def _remove_socket(self, s):
		self._remove_socket_by_s_id(id(s))

	def _remove_socket_by_s_id(self, s_id):
		l = self._sck.get(s_id)
		if l:
			del self._sck[s_id]
			del self._tol[s_id]
			s = l[1]
			self._rlst.discard(s)
			self._wlst.discard(s)
			s.close()

	def _recvall(self, f, s):
		try:
			d = s.recv(4096)
			if not d: return False
			while d:
				f.write(d)
				d = s.recv(4096)
		except socket.error, e:
			err = e.args[0]
			if err != errno.EAGAIN and err != errno.EWOULDBLOCK:
				return False

		return True

	def _sendall(self, q, s):
		try:
			while q:
				t = q[0]
				n = s.send(t[1][t[0]:t[0] + 4096])
				if not n: return False

				t[0] += n
				while n and t[0] < len(t[1]):
					n = s.send(t[1][t[0]:t[0] + 4096])
					t[0] += n

				if t[0] >= len(t[1]):
					q.pop(0)
				else:
					break

		except socket.error, e:
			err = e.args[0]
			if err != errno.EAGAIN and err != errno.EWOULDBLOCK:
				return False

		return True

	def _process(self, rl, wl, xl):
		for s in rl:
			s_id = id(s)
			if s == self._s:
				s, addr = s.accept()
				print "Connected:", addr
				s.setblocking(0)

				s_id = id(s)
				self._sck[s_id] = [ 1, s, cStringIO.StringIO(), int(time.time()), [] ]
				self._rlst.add(s)
				self._tol[s_id] = (int(time.time()), s)
			else:
				l = self._sck[s_id]
				ret = self._recvall(l[2], s)
				if not ret:
					print s.getpeername(), 'CLOSE(RECV)'
					self._remove_socket_by_s_id(s_id)
					continue

				del self._tol[s_id]
				self._tol[s_id] = (int(time.time()), s)

				self._parse_packet(l)

		for s in wl:
			s_id = id(s)
			l = self._sck.get(s_id)
			if not l: continue

			if l[4]:
				ret = self._sendall(l[4], s)
				if not ret:
					print s.getpeername(), 'CLOSE(SEND)'
					self._remove_socket_by_s_id(s_id)
					continue

				del self._tol[s_id]
				self._tol[s_id] = (int(time.time()), s)
			
			if not l[4]: self._wlst.discard(s)


		for s in xl:
			print s.getpeername(), 'CLOSE(ERROR)'
			self._remove_socket(s)

		cur_ts = int(time.time())
		if cur_ts - self._last_ts >= 6:
			lst = []
			for s_id,v in self._tol.items():
				last_ts,s = v
				if cur_ts - last_ts < self.idle_timeout: break
				lst.append(s_id)
				print s.getpeername(), "CLOSE(IdleTimout)"

			for s_id in lst: self._remove_socket_by_s_id(s_id)

			self._last_ts = int(time.time())

		while self._res:
			s,p = self._res.pop(0)
			l = self._sck.get(id(s))
			if l:
				l[4].append([0, self._build_packet(p)])
				self._wlst.add(s)

