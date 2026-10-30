# Instalar a Redmi NAS 0.2.0-rc3

Esta versão é experimental e destina-se exclusivamente ao Redmi Note 12 Pro+ 5G **22101316UG / rubypro / 256 GB**, com firmware **OS2.0.16.0.UMOEUXM** no slot **a**. Não usar noutros modelos, variantes 4G ou capacidades.

1. Desbloqueia previamente o bootloader com a ferramenta oficial Xiaomi e conclui a ativação da tua conta, se for pedida. O instalador não substitui o Mi Unlock. Guarda os dados: o desbloqueio e esta instalação apagam-nos.
2. Descarrega **RedmiNAS-Download.exe** da release. Escolhe uma pasta com espaço livre; o programa descarrega as partes, confere os SHA-256, junta o ZIP e abre o assistente. Em alternativa, junta manualmente as partes numeradas do ZIP, por ordem, e extrai-o.
3. Abre **RedmiNAS-Setup.exe**, escolhe a pasta do pacote e carrega em **Verificar**. Esta etapa não contacta o telefone. Preenche o modelo/firmware exigidos, escolhe um PIN Linux e, se quiseres, os dados Wi-Fi. O Windows precisa do Cliente OpenSSH para gerar uma chave individual.
4. Liga apenas o telefone destinado à instalação diretamente ao PC por USB, sem o hub. Entra em **FASTBOOT** com Ligar + Volume −. O assistente exige um único telefone e verifica produto, slot, desbloqueio e tamanhos de partições. O modelo e firmware devem ser conferidos pelo utilizador; o produto fastboot não identifica sozinho todas as variantes.
5. Lê e confirma o apagamento e carrega em **Instalar no telefone**. Se faltar fastboot, autoriza no assistente a descarga das Platform-Tools oficiais Google. Mantém o cabo ligado durante a gravação e a personalização USB. Não voltes a bloquear o bootloader.
6. O Linux arranca, recebe a tua configuração e instala a NAS automaticamente. Mantém alimentação e Internet; não é uma instalação totalmente offline. Se a personalização USB não terminar, usa **Retomar configuração USB**, que não volta a gravar as partições.
7. Na mesma rede, abre **http://redmi-nas.local** ou o IP atribuído pelo router e cria a tua conta Homeio. Steam e outras aplicações pedem as tuas próprias contas. Não vêm jogos, BIOS, filmes, sessões ou emparelhamentos.

## Proxmox opcional

Em Definições → Performance → Máquinas virtuais, o Homeio verifica KVM antes de preparar o Proxmox. A base ARM64 limpa está incluída, mas começa desligada. O telefone do projeto tem EL2 previamente preparado; desbloquear o bootloader, por si só, não garante EL2. Esta release não altera automaticamente os metadados de arranque para o ativar num aparelho de origem. Não instala um kernel Proxmox genérico. A NAS pode ser utilizada sem Proxmox.

O [guia bootloader → NAS → EL2/KVM → Proxmox](KVM-ACTIVATION.pt-PT.md) explica cada etapa, as verificações e a limitação atual: ainda falta um ativador EL2 público validado. Não é uma configuração que o utilizador tenha de descobrir sozinho.

## Âmbito do teste e recuperação

A rc2 passou a instalação física supervisionada no telefone do projeto. A rc3 mantém esse boot/layout e acrescenta userspace verificado no aparelho; não foi repetida uma instalação física completa da rc3 nem um teste num segundo aparelho. As cópias pessoais automáticas e opções de bateria/extensão de memória começam desligadas.

Se a gravação falhar, conserva FASTBOOT e o erro do assistente. Não uses imagens de outro modelo ou um vbmeta genérico. Esta instalação usa userdata em ext4: repor só boot Android não restaura o sistema de fábrica. A recuperação completa exige o firmware oficial correspondente ao modelo e região e o respetivo procedimento validado.

Projeto de José Miranda (Xcat2008), desenvolvido em Portugal. Consulta [os créditos](../CREDITS.md) e [as licenças](../THIRD_PARTY_NOTICES.md).
