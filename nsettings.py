#'CREATE TABLE users (username text, password text, files integer, mode text, low text, medium text, high text, files integer, risk text)'
LOCAL = False
VECTORS_ENABLED = True

#uncomment if local dev env
LOCAL = True
VECTORS_ENABLED = False

#terms for checking against phrase vectors (where the result is >0.8) in the user's document
GDPRVECTORS = '''your data,
your information,
sensitive information,
sensitive data,
personal information'''

#terms to check for simple matches against the user's document
GDPRWORDS = ''' personal information,
personally identifiable,
phone number,
personal data,
your data,
general data protection regulation,
your information,
european union,
gather data,
gather information,
private information,
private data,
data protection,
sensitive data,
sensitive information,
information about you,
information we collect,
data we collect,
information we collect,
we collect data,
we collect information,
share with us,
share information,
share data'''

QUESTIONS = ('Overall, I am satisfied with how easy it is to use this system.',
                        'It was simple to use this system.',
                        'I could effectively complete the tasks and scenarios using this system.',
                        'I was able to complete the tasks and scenarios quickly using this system.',
                        'I was able to efficiently complete the tasks and scenarios using this system.',
                        'I felt comfortable using this system.',
                        'It was easy to learn to use this system.',
                        'I believe I could become productive quickly using this system.',
                        'The system gave error messages that clearly told me how to fix problems.',
                        'Whenever I made a mistake using the system, I could recover easily and quickly.',
                        'The information (such as online help, on-screen messages, and other documentation) provided with this system was clear.',
                        'It was easy to find the information I needed.',
                        'The information provided for the system was easy to understand.',
                        'The information was effective in helping me complete the tasks and scenarios.',
                        'The organization of information on the system screens was clear.',
                        'The interface of this system was pleasant.',
                        'I liked using the interface of this system.',
                        'This system has all the functions and capabilities I expect it to have.',
                        'Overall, I am satisfied with this system.')
