from ibapi.client import EClient

class IBAPIClient(EClient):
	def __init__(self, wrapper):
		EClient.__init__(self, wrapper=self)