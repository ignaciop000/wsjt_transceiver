import threading
from multiprocessing import Process, Pipe
import os
import sys


def f(rpipe, wpipe, card, rate):
	rpipe.close()
	x = x_pya_input_rate(card, rate)
	print(x)
	wpipe.send(x)
	os._exit(0)
	
# find the lowest supported input rate >= rate.
# needed on Linux but not the Mac (which converts as needed).
def x_pya_input_rate(card, rate):
    import pyaudio
    rates = [ rate, 8000, 11025, 12000, 16000, 22050, 44100, 48000 ]
    for r in rates:
        if r >= rate:
            ok = False
            try:
                ok = pya().is_format_supported(r,
                                               input_device=card,
                                               input_format=pyaudio.paInt16,
                                               input_channels=1)
            except:
                pass
            if ok:
                return r
    sys.stderr.write("weakaudio: no input rate >= %d\n" % (rate))
    sys.exit(1)	

# sub-process to avoid initializing pyaudio in main
# process, since that makes subsequent forks and
# multiprocessing not work.
def pya_input_rate(card, rate):
	rpipe, wpipe = Pipe(False)
	p = Process(target=f, args=(rpipe,wpipe,card,rate,))
	p.start()
	p.join()
	wpipe.close()
	x = rpipe.recv()
	os.waitpid(pid, 0)
	rpipe.close()
	return x

# desc is [ "6", "0" ] for a sound card -- sixth card, channel 0 (left).
# desc is [ "sdrip", "192.168.1.2" ] for RFSpace SDR-IP.
def new(desc, rate):
	# sound card?
	if desc[0].isdigit():
		return Stream(int(desc[0]), int(desc[1]), rate)

#	if desc[0] == "sdrip":
#		return SDRIP(desc[1], rate)

#	if desc[0] == "sdriq":
#		return SDRIQ(desc[1], rate)

#	if desc[0] == "eb200":
#		return EB200(desc[1], rate)

#	if desc[0] == "sdrplay":
#		return SDRplay(desc[1], rate)

	sys.stderr.write("weakaudio: cannot understand card %s\n" % (desc[0]))
	usage()
	sys.exit(1)

class Stream:
	def __init__(self, card, chan, rate):		
		self.use_oss = False
		#self.use_oss = ("freebsd" in sys.platform)
		self.card = card
		self.chan = chan

		# UNIX time of audio stream time zero.
		self.t0 = None

		if rate == None:
			rate = pya_input_rate(card, 8000)

		self.rate = rate # the sample rate the app wants.
		self.cardrate = rate # the rate at which the card is running.

		self.cardbufs = [ ]
		self.cardlock = threading.Lock()

		self.last_adc_end = None
		self.last_end_time = None

		if self.use_oss:
			self.oss_open()
		else:
			self.pya_open()

		self.resampler = weakutil.Resampler(self.cardrate, self.rate)

		# rate at which len(self.raw_read()) increases.
		self.rawrate = self.cardrate

	def pya_open(self):
		self.cardrate = pya_input_rate(self.card, self.rate)
		
		# read from sound card in a separate process, since Python
		# scheduler seems sometimes not to run the py audio thread
		# often enough.
		sys.stdout.flush()
		rpipe, wpipe = multiprocessing.Pipe(False)
		proc = multiprocessing.Process(target=self.pya_dev2pipe, args=[rpipe,wpipe])
		proc.start()
		wpipe.close()
		self.rpipe = rpipe