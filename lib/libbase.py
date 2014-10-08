
mod_dbref = App.load('/dbref')

class LibBase:
	def __init__(self):
		self.__dbc__ = None

	def cur(self, new=False):
		mod_dbref.get(App.req)

		