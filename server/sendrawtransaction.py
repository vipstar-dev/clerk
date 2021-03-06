﻿#========================================================#
#                                                        #
#  VP-clerk: sendrawtransaction.py - TX 送出 queue       #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

from base_handler import BaseHandler
from base_handler import ValidationError
from coind import coind_factory
from hashlib import sha256
from base64 import b64decode
import logging
import json
import bz2

class handler( BaseHandler ):
	def post( self ):
		logging.getLogger().setLevel( logging.DEBUG )
		coind_type = self.get_request_coind_type()

		# payload を展開する
		try:
			payload = json.loads( bz2.decompress( b64decode( self.request.get( 'payload' ) ) ) )
		except ValueError as e:
			raise ValidationError( 'payload', e.message )
		except Exception as e:
			raise ValidationError( 'payload', 'decompress' )

		# payload のハッシュ値検査
		if sha256( payload['body'] ).hexdigest() != payload['hash']:
			raise ValidationError( 'payload', 'sha256' )

		# payload の本体をパースする
		try:
			payload = json.loads( payload['body'] )
		except ValueError as e:
			raise ValidationError( 'payload', e.message )

		# コインノードクライアントの初期化
		cd = coind_factory( coind_type )

		# コインノードに送信
		try:
			r = cd.run( 'sendrawtransaction', [ payload['tx'] ] )
		except Exception as e:
			# コインノードがエラーを返すと例外が飛んでくるのでもみ消してログを出す
			r = e.args


		# ロギング
		log_data = payload['log_data']
		log_data['result'] = r
		logging.debug(
			json.dumps( log_data, ensure_ascii=False, indent=2, sort_keys=True, separators=(',', ': ') )
		)


		# 作成した TXID を返す
		self.write_json( {
			'result': r
		} )
