// SPDX-License-Identifier: AGPL-3.0-only
import {readFile} from 'node:fs/promises';
import {upsertCustomStoreTemplate} from '@/lib/server/modules/store/custom-apps';
import {startStoreOperation,getStoreOperation} from '@/lib/server/modules/apps/operations';

async function main() {
  const source=await readFile('/var/lib/redmi-retroarch-homeio/docker-compose.yml','utf8');
  const app=await upsertCustomStoreTemplate({name:'RetroArch',iconUrl:'/retroarch-icon.svg',
    sourceType:'docker-compose',sourceText:source,
    repositoryUrl:'https://github.com/linuxserver/docker-retroarch'});
  if(app.appId!=='custom-retroarch') throw new Error('Unexpected custom app identifier');
  if(process.argv.includes('--register-only')) {
    console.log('Homeio gaming template ready');process.exit(0);
  }
  const op=await startStoreOperation({appId:app.appId,action:'install',
    displayName:'RetroArch',webUiPort:3443,composeSource:source});
  for(let i=0;i<1200;i++) {
    await new Promise(resolve=>setTimeout(resolve,2000));
    const state=await getStoreOperation(op.operationId);
    if(state?.status==='success') {console.log('Homeio gaming installed');process.exit(0);}
    if(state?.status==='error') throw new Error(state.message||'Homeio installation failed');
  }
  throw new Error('Homeio installation timed out');
}
main().catch(error=>{console.error(error.message);process.exit(1)});
