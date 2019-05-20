
class BaseCommand:
	def Set(self, pTokens):
		self.rawTokens = pTokens
	
	def IsValid(self):
		# Subclasses validate their information and return an error object
		return True
	
	def Execute(self, pShellState):
		# The base class purposely does nothing. To be implemented by subclasses
		return False

# Tasks to implement commands for
# Create mailbox
# Delete mailbox(?)
# Add user
# Delete user
# Add device
# Remove device
# Store item
# Download item
# Send item
# Get new items

gCommandMap = {
}

def handle_command(pTokens):
	if not pTokens:
		return True
	
	verb = pTokens[0].casefold()
	if verb == 'quit':
		return False
	
	print(' '.join(pTokens))
	return True
