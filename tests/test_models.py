import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import tempfile
import unittest
from pathlib import Path
from io import BytesIO
from unittest.mock import patch, Mock
from urllib.error import HTTPError
from PyQt6.QtWidgets import QApplication
from core.llm.cloud_client import CloudClient,CloudAPIError
from core.llm.chat_service import ChatService
from core.llm.contracts import ChatMessagePayload,ChatAttachmentPayload
from storage import database,model_store

app=QApplication.instance() or QApplication([])

class ModelTests(unittest.TestCase):
    def test_model_popup_opens_below_field_with_rounded_corners(self):
        from PyQt6.QtCore import QPoint
        from ui.model_controls import model_combo
        combo=model_combo()
        combo.resize(260,34)
        combo.move(50,50)
        combo.addItems(['first','second','third'])
        combo.show()
        app.processEvents()
        combo.showPopup()
        app.processEvents()
        popup=combo.view().window()
        self.assertEqual(popup.pos(),combo.mapToGlobal(QPoint(0,combo.height()+4)))
        self.assertEqual(popup.width(),combo.width())
        self.assertGreaterEqual(popup.height(),3*combo.view().sizeHintForRow(0))
        self.assertFalse(popup.mask().contains(QPoint(0,0)))
        combo.hidePopup()
        combo.close()

    def messages(self):
        return [ChatMessagePayload('system','system instructions'),ChatMessagePayload('user','hello'),ChatMessagePayload('assistant','hi'),ChatMessagePayload('user','followup')]

    def test_provider_payloads(self):
        for provider in ('openai','gemini','anthropic'):
            url,payload=CloudClient(provider,'fake').build_request('test-model',self.messages())
            self.assertTrue(url.startswith('https://'))
            self.assertNotIn('fake',json.dumps(payload))
            self.assertNotIn('fake',url)
            if provider=='openai':
                self.assertFalse(payload['store']);self.assertEqual(len(payload['input']),3)
            elif provider=='gemini':
                self.assertEqual(payload['contents'][1]['role'],'model')
                self.assertEqual(payload['systemInstruction']['parts'][0]['text'],'system instructions')
            else:
                self.assertEqual(payload['system'],'system instructions');self.assertEqual(payload['max_tokens'],4096)

    def test_streams(self):
        events={'openai':{'type':'response.output_text.delta','delta':'hello'},'anthropic':{'type':'content_block_delta','delta':{'type':'text_delta','text':'hello'}},'gemini':{'candidates':[{'content':{'parts':[{'text':'private thought','thought':True},{'text':'hello'}]}}]}}
        for provider,event in events.items():
            response=BytesIO(('data: '+json.dumps(event)+'\n\ndata: [DONE]\n').encode())
            with patch('core.llm.cloud_client.urlopen',return_value=response):
                self.assertEqual(''.join(CloudClient(provider,'fake').stream_chat('test',self.messages())),'hello')

    def test_safe_errors_and_missing_key(self):
        with patch('core.llm.cloud_client.get_key',return_value=''):
            with self.assertRaises(CloudAPIError):CloudClient('openai')._headers()
        for code in (401,404,429,500):
            with patch('core.llm.cloud_client.urlopen',side_effect=HTTPError('https://api.openai.com',code,'SECRET-KEY',{},None)):
                with self.assertRaises(CloudAPIError) as error:CloudClient('openai','SECRET-KEY').list_models()
                self.assertNotIn('SECRET-KEY',str(error.exception))

    def test_stream_failure_not_saved(self):
        client=ChatService(client=Mock());client.set_backend('openai','test')
        with patch('core.llm.cloud_client.CloudClient.stream_chat',side_effect=CloudAPIError('failed')):
            with self.assertRaises(CloudAPIError):list(client.send('hello'))
        self.assertEqual(client.history,())
        client._client.list_models.assert_not_called()

    def test_cloud_bypasses_ollama(self):
        local=Mock();service=ChatService(client=local);service.set_backend('gemini','test')
        service.warmup()
        with patch('core.llm.cloud_client.CloudClient.stream_chat',return_value=iter(['hello'])):
            self.assertEqual(''.join(service.send('안녕')),'hello')
        local.list_models.assert_not_called();local.warmup.assert_not_called()

    def test_model_config_survives_restart_without_credentials(self):
        with tempfile.TemporaryDirectory() as folder,patch('storage.database.db_path',return_value=Path(folder)/'test.db'):
            database.initialize();config=model_store.load()
            config['provider']='openai';config['models']['openai']='custom-model'
            model_store.save(config);self.assertEqual(model_store.load(),config)
            with database.get_connection() as conn:
                saved=conn.execute("SELECT value FROM preferences WHERE key='models'").fetchone()[0]
            self.assertNotIn('api_key',saved)

    def test_image_payload_all_providers(self):
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import Qt
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'image.bmp';image=QImage(8,8,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.red);image.save(str(file))
            messages=[ChatMessagePayload('user','image',(ChatAttachmentPayload.from_path(file),))]
            for provider in ('openai','gemini','anthropic'):
                url,payload=CloudClient(provider,'fake').build_request('model',messages)
                self.assertIn('image/png',json.dumps(payload))

    def test_keychain_only(self):
        with patch('keyring.backends.macOS.Keyring') as backend:
            model_store.set_key('openai','fake-key')
            backend.return_value.set_password.assert_called_once_with('Myorii API','openai','fake-key')

    def test_local_manager_download_link_and_delete(self):
        from ui.model_manager import ModelManager
        from PyQt6.QtWidgets import QMessageBox
        with patch.object(ModelManager,'refresh'):
            dialog=ModelManager('ollama','active')
        dialog.list.addItems(['active','other']);dialog.list.setCurrentRow(0)
        with patch('ui.model_manager.OllamaClient') as client:
            dialog.delete();client.assert_not_called()
            dialog.list.setCurrentRow(1)
            client.return_value.list_models.return_value=['active']
            def inline(operation,result):result(operation(lambda text:None))
            with patch.object(dialog,'start',side_effect=inline),patch('ui.model_manager.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
                dialog.delete()
            client.return_value._client.delete.assert_called_once_with('other')
            self.assertEqual(dialog.list.count(),1)
        with patch('ui.model_manager.QDesktopServices.openUrl') as open_url:
            dialog.install()
            self.assertEqual(open_url.call_args[0][0].toString(),'https://ollama.com/library')
        dialog.close()

    def test_mode_buttons_and_inline_password(self):
        from ui.settings_view import SettingsView
        from PyQt6.QtWidgets import QLineEdit
        with tempfile.TemporaryDirectory() as folder,patch('storage.database.db_path',return_value=Path(folder)/'test.db'):
            database.initialize();view=SettingsView()
            self.assertEqual(len(view.provider_control._buttons),2)
            self.assertEqual(view._model_pages.currentIndex(),0)
            view.provider_control._buttons[1].click()
            self.assertFalse(view.provider_control._buttons[0].isChecked())
            self.assertEqual(view._model_pages.currentIndex(),1)
            view.api_key.setText('fake-key')
            self.assertEqual(view.api_key.echoMode(),QLineEdit.EchoMode.Password)
            view.api_key.toggle.click()
            self.assertEqual(view.api_key.echoMode(),QLineEdit.EchoMode.Normal)
            view.provider_control._buttons[0].click()
            self.assertEqual(view.api_key.text(),'')
            self.assertEqual(view.api_key.echoMode(),QLineEdit.EchoMode.Password)
            view.close()

    def test_api_models_list(self):
        fixtures={'openai':{'data':[{'id':'gpt-test'},{'id':'embedding-test'}]},'anthropic':{'data':[{'id':'claude-test'}]},'gemini':{'models':[{'name':'models/gemini-test','supportedGenerationMethods':['generateContent']},{'name':'models/embedding','supportedGenerationMethods':['embedContent']}]}}
        for provider,data in fixtures.items():
            with patch('core.llm.cloud_client.urlopen',return_value=BytesIO(json.dumps(data).encode())):
                models=CloudClient(provider,'fake').list_models()
                self.assertEqual(len(models),1)
                self.assertNotIn('embedding',models[0])

    def test_chat_filter_and_paginated_models(self):
        for provider,ids in [('openai',['gpt-image-1','gpt-4o-audio-preview','gpt-4o-mini-search-preview','gpt-3.5-turbo']),('gemini',['gemini-test-image','gemini-test-tts'])]:
            for name in ids:
                self.assertFalse(CloudClient._chat_model(provider,{'id':name,'supportedGenerationMethods':['generateContent']}))
        pages=[{'data':[{'id':'claude-a'}],'has_more':True,'last_id':'claude-a'}, {'data':[{'id':'claude-b'}],'has_more':False}]
        with patch('core.llm.cloud_client.urlopen',side_effect=[BytesIO(json.dumps(page).encode()) for page in pages]) as request:
            self.assertEqual(CloudClient('anthropic','fake').list_models(),['claude-a','claude-b'])
            self.assertIn('after_id=claude-a',request.call_args.args[0].full_url)

    def test_save_key_loads_models_and_disallows_typing(self):
        from ui.main_window import MainWindow
        with tempfile.TemporaryDirectory() as folder,patch('storage.database.db_path',return_value=Path(folder)/'test.db'),patch('ui.main_window.ModelWarmupWorker.start'),patch('ui.main_window.ModelListWorker.start'),patch('ui.main_window.InternetStatusWatcher.check_now'):
            database.initialize();window=MainWindow();view=window._settings_view
            view.provider_control._buttons[1].click()
            self.assertFalse(view.api_model_combo.isEditable())
            view.api_key.setText('fake')
            def synchronous(operation,result):result(operation(lambda _:None))
            with patch.object(view,'_api_operation',side_effect=synchronous),patch('ui.settings_view.model_store.set_key') as save,patch('ui.settings_view.CloudClient.list_models',return_value=['gpt-a','gpt-b']) as fetch:
                view._save_api_key();save.assert_called_once_with('openai','fake');fetch.assert_called_once()
            self.assertEqual(view.api_model_combo.count(),2)
            self.assertEqual(window._chat_service.model,'gpt-a')
            view._apply_api_models('openai',['gpt-b'])
            self.assertEqual(window._chat_service.model,'gpt-b')
            view._apply_api_models('openai',[])
            self.assertEqual(window._chat_service.model,'')
            window.close()

    def test_provider_selection_persists(self):
        from ui.main_window import MainWindow
        with tempfile.TemporaryDirectory() as folder,patch('storage.database.db_path',return_value=Path(folder)/'test.db'),patch('ui.main_window.ModelWarmupWorker.start'),patch('ui.main_window.ModelListWorker.start'),patch('ui.main_window.InternetStatusWatcher.check_now'):
            database.initialize();window=MainWindow()
            window._settings_view.provider_control._buttons[1].click()
            window._settings_view._apply_api_models('openai',['gpt-test'])
            window._settings_view._api_model_selected()
            self.assertEqual(window._chat_service._provider,'openai')
            self.assertEqual(window._chat_service.model,'gpt-test')
            reopened=MainWindow()
            self.assertEqual(reopened._chat_service.model,'gpt-test')
            self.assertEqual(reopened._settings_view.api_model_combo.currentText(),'gpt-test')
            window.close();reopened.close()

if __name__=='__main__':unittest.main()
