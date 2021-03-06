﻿#========================================================#
#                                                        #
#  VP-clerk: gettransaction.py - TX 情報取得             #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from base_handler import BaseHandler
from cloudsql import CloudSQL
from util import SATOSHI_COIN
from webob import exc
import json
import base64
import bz2

class handler( BaseHandler ):
	def get( self ):
		coind_type = self.get_request_coind_type()
		txid = self.request.get('txid')
		height = self.request.get('height', None)

		db = CloudSQL( coind_type )
		with db as c:
			# 現在のブロック高を取得する
			c.execute( 'SELECT MAX(height) FROM blockheader' )
			chain_height = c.fetchone()['MAX(height)']

			# トランザクション情報を取得
			if height is None:
				c.execute( 'SELECT * FROM transaction WHERE txid = %s', (txid,) )
			else:
				c.execute( 'SELECT * FROM transaction WHERE txid = %s AND height = %s', (txid, height) )

			r = []
			for e in c.fetchall():
				# コインノードからの生データをパース
				json_txdata = json.loads( bz2.decompress( base64.b64decode( e['json'] ) ) )

				# vin_n の想定数を数える
				vin_n = 0
				for ee in json_txdata['vin']:
					if ee.has_key('txid'):
						vin_n += 1

				# vin の情報を追加する
				c.execute( 'SELECT * FROM transaction_link WHERE vin_height = %s AND vin_txid = %s ORDER BY vin_idx', (e['height'], e['txid']) )
				vin_link = c.fetchall()
				if len( vin_link ) != vin_n:
					raise Exception( e['height'], e['txid'], len( vin_link ), vin_n, 'mismatch and vin_link and vin_n' )

				for i in range( vin_n ):
					json_txdata['vin'][i]['value'] = vin_link[i]['value'] / SATOSHI_COIN
					json_txdata['vin'][i]['height'] = vin_link[i]['vout_height']
					json_txdata['vin'][i]['txid'] = vin_link[i]['vout_txid']
					if json_txdata['vin'][i].has_key( 'scriptSig' ):
						json_txdata['vin'][i]['scriptSig']['addresses'] = vin_link[i]['addresses'].split(' ')

				# vout 方向のリンクを追加する
				c.execute( 'SELECT * FROM transaction_link WHERE vout_height = %s AND vout_txid = %s ORDER BY vout_idx', (e['height'], e['txid']) )
				vout_link = c.fetchall()
				if len( vout_link ) != e['vout_n']:
					raise Exception( e['height'], e['txid'], len( vout_link ), e['vout_n'], 'mismatch and vout_link and vout_n' )

				for i in range( e['vout_n'] ):
					json_txdata['vout'][i]['scriptPubKey']['txid'] = vout_link[i]['vin_txid']
					json_txdata['vout'][i]['scriptPubKey']['height'] = vout_link[i]['vin_height']

				# 確認数を追加する
				json_txdata['confirmations'] = chain_height - e['height'] + 1

				# 高さを追加
				json_txdata['height'] = e['height']

				r.append( json_txdata )

		if len( r ) == 0:
			# 存在しない場合
			raise exc.HTTPNotFound()

		# JSON 形式でシリアライズして返す
		if height is None:
			self.write_json( r )
		else:
			self.write_json( r[0] )
