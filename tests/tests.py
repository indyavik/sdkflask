"""
:test flask app using unittest 
"""
from app import app
import unittest 
import os
import json
from ../../cron import helpers 

class BasicTestCase(unittest.TestCase):

	def test_index(self):
		""" ensure flask is set up and responding """
		tester = app.test_client(self)
		repsonse = tester.get('/', content_type='html/text')
		self.assertEqual(repsonse.status_code, 200)

	def test_not_exists(self):
		""" 404 on non existent routes """
		tester = app.test_client(self)
		repsonse = tester.get('/nonExistanceURL', content_type='html/text')
		self.assertEqual(repsonse.status_code, 404)


	def test_submit(self): 
		""" correct parsing, and error conditions """
		
		tester = app.test_client(self)

		rv = tester.post('/submit', data=dict(phone_field='1203456789'), follow_redirects=True)
		assert '(120)345-6789' in rv.data 

		rv = tester.post('/submit', data=dict(phone_field='+12034567899'), follow_redirects=True)
		assert '(203)456-7899' in rv.data

		#only us numbers (leading +7 followed by 10 digt number)
		rv = tester.post('/submit', data=dict(phone_field='+7203-4567-890'), follow_redirects=True)
		assert 'error' in rv.data

		#test dates are dropped and error is raised
		rv = tester.post('/submit', data=dict(phone_field='11.11.1900'), follow_redirects=True)
		assert 'error' in rv.data

		rv = tester.post('/submit', data=dict(phone_field='(203) 455 8989 some text follows'), follow_redirects=True)
		assert '(203)455-8989' in rv.data

		rv = tester.post('/submit', data=dict(phone_field='(203).455.(8989) some text follows'), follow_redirects=True)
		assert '(203)455-8989' in rv.data


if __name__ == '__main__' : 
	unittest.main()
