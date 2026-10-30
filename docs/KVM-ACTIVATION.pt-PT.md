# Bootloader, EL2 e Proxmox: o percurso completo e o estado atual

**A NAS pode ser instalada sem Proxmox. A rc3 ainda não automatiza a preparação EL2 de um telefone de origem.** Não há um comando escondido que o utilizador deva adivinhar. Esta é uma etapa por concluir, e não um requisito satisfeito apenas pelo Mi Unlock.

## 1. Preparar o telefone e instalar a NAS

Confirma **Redmi Note 12 Pro+ 5G, 22101316UG, rubypro, 256 GB**, firmware **OS2.0.16.0.UMOEUXM**, slot **a**. Outras capacidades e variantes não estão aprovadas. Guarda os dados e o firmware oficial de recuperação fora do telefone.

Desbloqueia o bootloader pelo processo oficial Xiaomi. É o proprietário que resolve os requisitos da conta, a espera e a ativação após o apagamento. O projeto não inclui desbloqueio de contas, nem contorna esses requisitos.

Segue o [assistente Windows](INSTALL-WIZARD.pt-PT.md): descarregar, verificar o pacote, escolher credenciais individuais, ligar em FASTBOOT e confirmar a instalação que apaga os dados. O primeiro arranque instala a NAS com Internet. Cria depois a tua conta Homeio. Não é necessário ativar Proxmox para usar ficheiros, aplicações ou multimédia.

## 2. Verificar a virtualização antes de instalar Proxmox

Há três condições diferentes:

| Condição | O que permite | Como se verifica |
| --- | --- | --- |
| Bootloader desbloqueado | Instalar o arranque Linux compatível | Verificação FASTBOOT do assistente |
| EL2 entregue ao Linux pela plataforma | Usar o nível de execução ARM necessário ao KVM | Registo de arranque e teste efetivo do KVM; não se infere do desbloqueio |
| Kernel KVM e módulos correspondentes | Expor a interface de virtualização | API de `/dev/kvm`, seguida da criação de uma VM de teste |

O componente GenieZone da MediaTek pode ocupar EL2 antes do Linux. A [documentação técnica da MediaTek](https://lists.infradead.org/pipermail/linux-mediatek/2024-January/074896.html) descreve esse hipervisor nesse nível. Isso explica a distinção; não prova compatibilidade de uma alteração com todos os telefones MediaTek.

No código atual, podes executar, na raiz de uma cópia do repositório no telefone:

```sh
sudo python3 kernel/kvm/check_readiness.py
```

O diagnóstico é só de leitura: não altera partições, não instala um kernel e não inicia uma VM. Uma falha de permissões é apresentada separadamente. A ausência de `/dev/kvm` não é tratada, por si só, como prova de que falta EL2.

- `kvm-api-available`: a API respondeu; prossegue para a preparação opcional nas definições. Ainda é preciso o teste real de criação de VM.
- `permissions-required`: repete com privilégios; não alteres o arranque por causa desta mensagem.
- `platform-or-kernel-not-ready`: a preparação da plataforma ou do kernel falta. **A rc3 não resolve automaticamente este estado.** Instalar pacotes Proxmox não o resolve.
- `unsupported-profile`: não aplicar esta integração ao modelo/kernel em causa.

## 3. A etapa EL2 que funcionou no aparelho do projeto

O ensaio que permitiu arrancar em EL2 alterou os campos de localização de duas entradas GenieZone na tabela de partições, mantendo os nomes e sem copiar os conteúdos das partições. Não foi uma simples opção do Linux. A experiência anterior de mudar apenas os nomes não funcionou e não é um procedimento recomendado.

O teste utilizou recuperação USB/BootROM e cópias próprias dos metadados, verificadas antes e depois da escrita. Não se devem distribuir ou reutilizar a tabela de partições de outro aparelho, identificadores individuais, preloader, firmware TEE/LK ou cópias do autor. O firmware original permanece a cargo do proprietário do dispositivo.

**Ainda não há neste repositório um executor público dessa alteração.** Os testes de instalação limpa ocorreram no aparelho que já tinha EL2 preparado; portanto não demonstram a passagem automática de um telefone de origem para EL2. Uma ferramenta pública precisa de identificar o modelo, firmware e layout de cada unidade, guardar a sua própria recuperação, restringir as alterações, verificar as duas tabelas e demonstrar recuperação física. A publicação de um botão que apenas escrevesse valores de outro telefone daria uma falsa garantia.

Esta documentação descreve o resultado técnico, não concede autorização jurídica universal para alterar proteções de firmware. O âmbito de uma eventual distribuição dessa ferramenta precisa de ser avaliado separadamente; ver [revisão de distribuição](DISTRIBUTION-REVIEW.pt-PT.md).

## 4. Ativar o Proxmox quando o KVM está funcional

Abre **Definições → Performance → Máquinas virtuais · Proxmox** no Homeio. A base ARM64 limpa vem incluída e desligada. A preparação verifica capacidades, configura o ambiente isolado e a rede privada e pede uma palavra-passe própria de pelo menos oito caracteres. O diagnóstico anterior, sozinho, não substitui estas verificações.

Usa **Abrir Proxmox**, que abre HTTPS na porta 8006 do endereço atual da NAS. Entra como `root`, domínio **Linux PAM**, com a palavra-passe que escolheste. Não são fornecidas contas do autor ou uma palavra-passe partilhada.

O ambiente partilha os oito CPUs físicos e a RAM disponível com a NAS; não duplica memória. As VMs devem deixar recursos para o sistema. Usa convidados **ARM64/aarch64**, CPU `host`, UEFI, disco EFI persistente, VirtIO/SCSI e a bridge privada `vmbr0`. A rede privada fornece DHCP/DNS e saída por NAT; não cria um servidor DHCP na rede doméstica. A [validação Proxmox](PROXMOX.md) distingue o que já passou dos recursos ainda não testados.

Não instales um kernel genérico Proxmox sobre o kernel do telefone, não substituas o LXC de hardware do Droidian e não voltes a bloquear o bootloader com este sistema instalado.

## Estado de distribuição

O diagnóstico e estas instruções estão no código-fonte após a rc3. Não alteram retroativamente os ficheiros já publicados dessa release. A NAS rc3 é instalável dentro do perfil experimental descrito; a instalação opcional do Proxmox exige KVM funcional. A ativação EL2 automática num aparelho de origem permanece por validar e distribuir.
