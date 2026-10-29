#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 José Miranda (Xcat2008)
"""Windows installation assistant. Verification is always non-destructive."""
import contextlib
import json
from pathlib import Path
import queue
import shutil
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
import installer

GUIDE='https://github.com/Xcat2008/redmi-note12proplus-nas/blob/main/docs/INSTALL-WIZARD.pt-PT.md'


class QueueOutput:
    def __init__(self,events):self.events=events
    def write(self,text):
        if text:self.events.put(('log',text))
    def flush(self):pass


class Wizard:
    def __init__(self,root,folder):
        self.root=root;self.events=queue.Queue();self.busy=False;self.manifest=None
        root.title('Redmi NAS — Instalação');root.geometry('840x760');root.minsize(740,680)
        root.protocol('WM_DELETE_WINDOW',self.close)
        outer=ttk.Frame(root,padding=22);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='Redmi NAS',font=('Segoe UI',24,'bold')).pack(anchor='w')
        ttk.Label(outer,text='José Miranda · Xcat2008 · Desenvolvido em Portugal').pack(anchor='w',pady=(0,15))
        self.status=tk.StringVar(value='1. Verifica o pacote antes de ligar o telefone.')
        ttk.Label(outer,textvariable=self.status,wraplength=760).pack(anchor='w',pady=(0,12))
        files=ttk.LabelFrame(outer,text='Pacote de instalação',padding=12);files.pack(fill='x')
        self.folder=tk.StringVar(value=str(folder))
        ttk.Entry(files,textvariable=self.folder,state='readonly').pack(side='left',fill='x',expand=True)
        self.choose=ttk.Button(files,text='Escolher pasta',command=self.select);self.choose.pack(side='left',padx=(8,0))
        self.verify=ttk.Button(files,text='Verificar',command=self.check);self.verify.pack(side='left',padx=(8,0))
        self.detail=tk.StringVar(value='A verificação não acede ao telefone nem apaga dados.')
        ttk.Label(outer,textvariable=self.detail,wraplength=760).pack(anchor='w',pady=12)
        form=ttk.LabelFrame(outer,text='Configuração pessoal',padding=12);form.pack(fill='x')
        self.fields={}
        rows=[('model','Modelo impresso no telefone','22101316UG',False),('firmware','Firmware Android de origem','OS2.0.16.0.UMOEUXM',False),('pin','Novo PIN Linux (4–12 números)','',True),('repeat','Repetir PIN','',True),('ssid','Wi-Fi (opcional)','',False),('password','Palavra-passe Wi-Fi','',True)]
        for row,(name,label,value,secret) in enumerate(rows):
            ttk.Label(form,text=label).grid(row=row,column=0,sticky='w',pady=3)
            var=tk.StringVar(value=value);self.fields[name]=var
            ttk.Entry(form,textvariable=var,show='•' if secret else '').grid(row=row,column=1,sticky='ew',padx=(12,0),pady=3)
        form.columnconfigure(1,weight=1)
        self.erase=tk.BooleanVar(value=False)
        ttk.Checkbutton(outer,text='Tenho cópia dos dados e aceito apagar Android e todos os ficheiros deste telefone.',variable=self.erase).pack(anchor='w',pady=(12,4))
        ttk.Label(outer,text='Bootloader desbloqueado pela Xiaomi · apenas o modelo e firmware indicados.',wraplength=760).pack(anchor='w')
        buttons=ttk.Frame(outer);buttons.pack(fill='x',pady=12)
        self.install=ttk.Button(buttons,text='Instalar no telefone',command=self.start_install,state='disabled');self.install.pack(side='left')
        self.setup=ttk.Button(buttons,text='Retomar configuração USB',command=self.resume,state='disabled');self.setup.pack(side='left',padx=8)
        ttk.Button(buttons,text='Instruções completas',command=lambda:webbrowser.open(GUIDE)).pack(side='right')
        self.progress=ttk.Progressbar(outer,mode='indeterminate');self.progress.pack(fill='x')
        self.log=tk.Text(outer,height=9,wrap='word',state='disabled',font=('Consolas',9));self.log.pack(fill='both',expand=True,pady=(10,0))
        root.after(100,self.drain)

    def select(self):
        folder=filedialog.askdirectory(initialdir=self.folder.get())
        if folder:self.folder.set(folder);self.manifest=None;self.install.configure(state='disabled');self.setup.configure(state='disabled')

    def run(self,job):
        if self.busy:return
        self.busy=True;self.progress.start(12)
        for button in (self.verify,self.choose,self.install,self.setup):button.configure(state='disabled')
        def worker():
            try:
                with contextlib.redirect_stdout(QueueOutput(self.events)):
                    job()
            except Exception as error:self.events.put(('error',str(error)))
            finally:self.events.put(('done',None))
        threading.Thread(target=worker,daemon=True).start()

    def check(self):
        folder=Path(self.folder.get())
        def job():
            manifest=installer.inspect_package(folder)
            self.events.put(('verified',manifest))
        self.run(job)

    def values(self):
        values={key:var.get() for key,var in self.fields.items()}
        if values['model']!='22101316UG':raise ValueError('Este pacote só suporta o modelo 22101316UG.')
        if not self.manifest or values['firmware']!=self.manifest['factory_firmware']:raise ValueError('Confirma o firmware de origem exigido pelo pacote.')
        if values['pin']!=values['repeat']:raise ValueError('Os dois PINs não coincidem.')
        if not installer.re.fullmatch(r'[0-9]{4,12}',values['pin']):raise ValueError('O PIN deve conter 4 a 12 números.')
        if values['ssid']:
            if not 1<=len(values['ssid'].encode())<=32 or any(ord(c)<32 for c in values['ssid']):raise ValueError('Nome de Wi-Fi inválido.')
            if not 8<=len(values['password'])<=63 or any(ord(c)<32 for c in values['password']):raise ValueError('Palavra-passe WPA inválida.')
        if not shutil.which('ssh-keygen'):raise ValueError('Instala o Cliente OpenSSH nas funcionalidades opcionais do Windows antes de continuar.')
        return values

    def start_install(self):
        try:
            installer.require_release(self.manifest or {})
            values=self.values()
            if not self.erase.get():raise ValueError('É necessário aceitar o apagamento do telefone.')
        except ValueError as error:messagebox.showerror('Ainda não é possível instalar',str(error));return
        if not messagebox.askyesno('Apagar este telefone?', 'A instalação apaga Android, contas e ficheiros. O Redmi deve estar em FASTBOOT, ligado por USB. Continuar?'):return
        download=messagebox.askyesno('Ferramentas Android','Se faltarem, autorizas descarregar as Platform-Tools oficiais da Google?')
        folder=Path(self.folder.get())
        def job():
            import serial  # Validate the dependency before writing anything.
            manifest=installer.inspect_package(folder);installer.require_release(manifest)
            executable=installer.locate_fastboot(folder,None,authorize_download=lambda:download)
            target=installer.device_preflight(executable,manifest)
            fields,key=installer.make_setup_fields(values['pin'],values['ssid'],values['password'])
            installer.flash_images(executable,target,folder,manifest)
            installer.command(executable,target,'reboot')
            print('A aguardar a configuração USB do Linux.',flush=True)
            installer.personalize(fields)
            self.events.put(('installed',str(key)))
        self.run(job)

    def resume(self):
        try:installer.require_release(self.manifest or {});values=self.values()
        except ValueError as error:messagebox.showerror('Configuração',str(error));return
        def job():
            fields,key=installer.make_setup_fields(values['pin'],values['ssid'],values['password'])
            installer.personalize(fields);self.events.put(('installed',str(key)))
        self.run(job)

    def drain(self):
        while True:
            try:kind,data=self.events.get_nowait()
            except queue.Empty:break
            if kind=='log':
                self.log.configure(state='normal');self.log.insert('end',data);self.log.see('end');self.log.configure(state='disabled')
            elif kind=='verified':
                self.manifest=data
                ready=data.get('physical_install_test_passed') and data.get('binary_redistribution_audit_passed')
                self.status.set('Pacote verificado. '+('Preenche a configuração e liga o Redmi em FASTBOOT.' if ready else 'Candidato de testes: instalação normal bloqueada.'))
                self.detail.set(data['version']+' · '+data['device']+'\n'+('Versão aprovada para instalação.' if ready else 'Ainda faltam validação física e aprovação de distribuição. A verificação do pacote não valida o arranque num telefone.'))
            elif kind=='error':self.status.set('Operação interrompida. Consulta a mensagem.');messagebox.showerror('Redmi NAS',data)
            elif kind=='installed':
                self.status.set('Linux configurado. A instalação dos serviços continua no telefone quando houver Internet.')
                self.fields['pin'].set('');self.fields['repeat'].set('');self.fields['password'].set('')
                messagebox.showinfo('Configuração enviada','Mantém o telefone alimentado e ligado à rede. O primeiro arranque descarrega e configura os serviços.\n\nA chave SSH privada fica neste PC: '+data+'\n\nDepois abre http://redmi-nas.local e cria a tua conta Homeio.')
            elif kind=='done':
                self.busy=False;self.progress.stop()
                for button in (self.verify,self.choose):button.configure(state='normal')
                ready=self.manifest and self.manifest.get('physical_install_test_passed') and self.manifest.get('binary_redistribution_audit_passed')
                for button in (self.install,self.setup):button.configure(state='normal' if ready else 'disabled')
        self.root.after(100,self.drain)

    def close(self):
        if self.busy:messagebox.showwarning('Operação em curso','Espera que a operação termine antes de fechar. Não desligues o cabo durante uma gravação.');return
        self.root.destroy()


def main():
    folder=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    if '--folder' in sys.argv:folder=Path(sys.argv[sys.argv.index('--folder')+1]).resolve()
    root=tk.Tk()
    if '--self-test-output' in sys.argv:
        root.withdraw();ui=Wizard(root,folder);root.update_idletasks()
        assert str(ui.install['state'])=='disabled'
        ui.events.put(('verified',{'version':'self-test','device':'self-test','physical_install_test_passed':False,'binary_redistribution_audit_passed':False}));ui.events.put(('done',None));ui.drain()
        assert str(ui.install['state'])=='disabled'
        output=Path(sys.argv[sys.argv.index('--self-test-output')+1])
        output.write_text(json.dumps({'gui_started':True,'candidate_install_blocked':True,'device_accessed':False})+'\n',encoding='utf-8')
        root.destroy();return
    Wizard(root,folder);root.mainloop()


if __name__=='__main__':main()
