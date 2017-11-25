# This skeleton script is designed to just get you started. When called, this file gets passed the phone object
# from phonehomey. Furthermore, all globals (functions, classes, objects, etc) from the main phonehomey code are 
# available to this script and can be used directly. Proceed with caution!
#
# If you want access to the phonehomey config file (for instance, if you want to add your own values to it), you can 
# import it by calling and acces all of the properties. Say you added output_path = ./output/ to the globals section:
#
# 	config = read_config()
#   output_path = config['global']['output_path']
#
# At startup the phone instance (the phone that is triggering the event that called this script) is passed into the 
# main function. This allows you to introspect the phone and use those properties in your code. This is shown below
# in the main function.
#
# For logging call log.debug() to log only in debug mode or log.info() to always logged the message. This script will 
# log along with phonehomey to the same log file. The module name (this scripts name) will be included in the log 
# format so you can see what module is logging what.


def main(phone, all_phones):
	if not all_phones:
		# the two likely properties you might want from phone are the name and location (home or away)
		log.debug('run code for {} at location: {}'.format(phone.name, phone.location))
		# for further exploration, this is the full list of phone properties (look at output in debug mode)
		log.debug('phone properties: {}'.format(phone.__dict__))
	elif phone.location == 'home':
		log.debug('run code for all phones being home')
	elif phone.location == 'away':
		log.debug('run code for all phones being away')


if __name__ == '__main__':
    main(locals()['phone'], locals()['all_phones'])