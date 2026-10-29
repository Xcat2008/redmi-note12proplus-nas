# Instalar a NAS no Redmi

O objetivo é descarregar um pacote, abrir o assistente no Windows e deixar a configuração inicial a cargo do instalador. Não é necessário compilar Linux nem copiar comandos de partições.

**Estado atual: candidato de testes. Ainda não há uma versão aprovada para instalação pública.** O assistente permite verificar o pacote, mas mantém a instalação normal bloqueada enquanto faltarem o teste físico de raiz e a revisão de distribuição. A existência de um `.exe` não significa que esses testes já passaram.

O primeiro teste supervisionado apagou e reinstalou o telefone do projeto, com autorização do proprietário. A personalização USB, o Wi-Fi e o Homeio arrancaram; esse teste revelou dependências e uma ordem de arranque que estão agora corrigidas no código. A instalação completa sem intervenções ainda precisa de ser repetida com a candidata corrigida.

## O telefone certo

Este perfil destina-se exclusivamente ao **Redmi Note 12 Pro+ 5G, modelo 22101316UG, 256 GB**, com firmware de origem **OS2.0.16.0.UMOEUXM**, slot `a`, e bootloader desbloqueado pela Xiaomi. O nome comercial, por si só, não chega: os modelos 4G, outras capacidades e outras variantes não estão validados.

O desbloqueio e a instalação apagam dados. Guarda os ficheiros e dados das aplicações que pretendas manter. Conclui a ativação da tua conta Xiaomi, se o fabricante a pedir. O assistente não desbloqueia contas nem substitui o Mi Unlock.

## Quando houver uma versão aprovada

1. Descarrega o pacote da secção **Releases** deste repositório. Confirma que a versão está marcada como aprovada para o teu modelo. Não uses um pacote de testes para atualizar uma NAS com dados.
2. Extrai o ZIP para uma pasta do PC, num disco com espaço. Não executes o programa de dentro do ZIP.
3. Abre **RedmiNAS-Setup.exe**. Escolhe a pasta extraída e carrega em **Verificar**. O assistente confere tamanho, SHA-256 e estrutura das imagens, sem contactar o telefone.
4. Preenche o modelo e o firmware exigidos. Escolhe o teu PIN Linux e, se quiseres, os dados do Wi-Fi. O assistente cria uma chave SSH nova no teu computador; não vem uma palavra-passe do autor.
5. Desliga outros telefones do PC. No Redmi destinado à instalação, entra em **FASTBOOT** com Ligar + Volume − e liga-o diretamente por USB, sem o hub. O assistente exige um único telefone e verifica o produto, slot, desbloqueio e tamanhos das partições.
6. Lê e aceita a confirmação de apagamento. Carrega em **Instalar no telefone**. Se forem necessárias as Platform-Tools, o assistente pede autorização para descarregar as ferramentas oficiais da Google. O instalador grava `userdata` e `boot_a` e preserva os metadados AVB do firmware original exigido. Não desligues o cabo nem feches o assistente durante a gravação.
7. O Linux arranca e recebe a configuração pelo USB. Mantém o telefone alimentado e com acesso à Internet: o primeiro arranque descarrega os pacotes e configura a NAS. Não há contas Steam, jogos, BIOS, ficheiros pessoais ou emparelhamentos incluídos.
8. Abre **http://redmi-nas.local** no PC da mesma rede e cria a tua conta Homeio. Se o nome não resolver, consulta o endereço do telefone na lista de dispositivos do router.

O Cliente OpenSSH do Windows deve estar disponível para gerar a chave. O assistente informa se faltar. Não é necessário instalar Python para usar o executável distribuído; o código Python continua disponível para auditoria e manutenção.

## Se a configuração USB não terminar

Mantém o cabo ligado e usa **Retomar configuração USB** no assistente. Esta operação envia a configuração inicial; não volta a gravar `userdata` ou `boot`. Se já tiver sido concluída, o telefone não aceita uma nova personalização por esse serviço.

Se a gravação falhar, guarda o erro apresentado e conserva o telefone em FASTBOOT. Não experimentes ficheiros de outros modelos nem voltes a bloquear o bootloader. Uma NAS instalada usa `userdata` em ext4; restaurar apenas a imagem de arranque Android não devolve o telefone ao estado de fábrica. Para recuperação completa é necessário o firmware oficial correspondente ao modelo/região e um procedimento validado para esse aparelho.

Os metadados AVB do fabricante devem manter-se intactos. O teste físico do perfil 0.2.0-rc1 falhou quando estes foram substituídos por um `vbmeta.img` vazio e genérico; o mesmo novo arranque funcionou ao conservar os originais. Esse perfil foi retirado e o cliente corrigido rejeita-o antes de escrever dados. O bootloader continua a ter de estar desbloqueado, e o firmware original tem de corresponder exatamente ao indicado. A imagem de arranque Linux não tem uma assinatura de confiança da Xiaomi. A instalação limpa completa continua a exigir validação física; a verificação estrutural no PC não a substitui.

## O que está incluído

A candidata reúne Linux/Droidian, as adaptações de hardware e a configuração automática do Homeio, RetroArch, Steam e Sunshine. O perfil de vídeo Jellyfin está incluído e é aplicado quando o Jellyfin é instalado pela loja Homeio. Parte dos programas é descarregada de fontes oficiais no primeiro arranque, pelo que este não é um instalador totalmente offline. As aplicações e contas que exigem início de sessão continuam a ser configuradas por cada utilizador.

As cópias pessoais automáticas, a extensão de memória no armazenamento e os controlos opcionais da bateria começam desligados. As proteções térmicas mantêm-se ativas.

## Proxmox e máquinas virtuais

O pacote em preparação inclui uma base Proxmox ARM64 limpa e as correções para os oito núcleos, como componente opcional. O serviço começa **desligado**, sem contas do autor e sem máquinas virtuais.

Há uma condição adicional: o arranque tem de entregar o processador em **EL2**, e o kernel tem de expor KVM funcional. No telefone do projeto foi necessária uma alteração específica de metadados de arranque. A instalação normal **não aplica automaticamente essa alteração**. Instalar Linux ou selecionar uma opção não a substitui.

Por isso, a candidata ainda não é uma solução pública de Proxmox de um clique. A ativação de raiz, o reinício completo e a recuperação precisam de validação física antes de se desbloquear essa distribuição. Num ambiente que já tenha EL2/KVM validado, o preparador verifica a compatibilidade antes de ativar serviços e pede uma palavra-passe própria. Consulta o [estado técnico do Proxmox](PROXMOX.md).

## Para quem vai testar a candidata

O modo experimental por linha de comandos é apenas para uma instalação física supervisionada, com possibilidade de recuperar o aparelho. Não é um passo que os utilizadores normais devam seguir para contornar o bloqueio do assistente. O teste tem de registar a gravação, primeiro arranque, configuração, rede, serviços, reinício completo e recuperação. Os resultados só serão marcados como aprovados depois de terem acontecido.

Projeto de José Miranda (Xcat2008), desenvolvido em Portugal. Os créditos dos projetos utilizados estão em [CREDITS.md](../CREDITS.md).
