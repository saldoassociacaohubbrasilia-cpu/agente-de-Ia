import { useCallback, useEffect, useState } from 'react'
import { buscarConversa, enviarPergunta, listarConversas } from '../lib/api.js'
import BarraMais from '../componentes/BarraMais.jsx'
import Sidebar from '../componentes/Sidebar.jsx'
import JanelaChat from '../componentes/JanelaChat.jsx'
import CaixaDeEntrada from '../componentes/CaixaDeEntrada.jsx'
import './Conversa.css'

let proximoIdTemporario = 1

function Conversa({ token, perfil, aoSair }) {
  const [conversas, definirConversas] = useState([])
  const [conversaAtualId, definirConversaAtualId] = useState(null)
  const [mensagens, definirMensagens] = useState([])
  const [carregandoMensagens, definirCarregandoMensagens] = useState(false)
  const [enviando, definirEnviando] = useState(false)
  const [erro, definirErro] = useState('')

  const recarregarConversas = useCallback(async () => {
    try {
      const lista = await listarConversas(token)
      definirConversas(lista)
    } catch (erroLista) {
      if (erroLista.status === 401) {
        aoSair()
        return
      }
      definirErro(erroLista.message)
    }
  }, [token, aoSair])

  useEffect(() => {
    recarregarConversas()
  }, [recarregarConversas])

  async function selecionarConversa(id) {
    definirErro('')
    definirConversaAtualId(id)
    definirCarregandoMensagens(true)
    try {
      const detalhe = await buscarConversa(token, id)
      definirMensagens(detalhe.mensagens)
    } catch (erroDetalhe) {
      if (erroDetalhe.status === 401) {
        aoSair()
        return
      }
      definirErro(erroDetalhe.message)
    } finally {
      definirCarregandoMensagens(false)
    }
  }

  function iniciarNovaConversa() {
    definirErro('')
    definirConversaAtualId(null)
    definirMensagens([])
  }

  async function enviarMensagem(pergunta) {
    definirErro('')
    const mensagemProfessor = {
      id: `temp-${proximoIdTemporario++}`,
      autor: 'professor',
      texto: pergunta,
      fontes: null,
      chamado_id: null,
    }
    definirMensagens((atual) => [...atual, mensagemProfessor])
    definirEnviando(true)

    try {
      const resultado = await enviarPergunta(token, pergunta, conversaAtualId)

      const mensagemAgente = {
        id: `temp-${proximoIdTemporario++}`,
        autor: 'agente',
        texto: resultado.resposta,
        fontes: resultado.fontes,
        chamado_id: resultado.chamado_id,
      }
      definirMensagens((atual) => [...atual, mensagemAgente])

      const primeiraMensagemDaConversa = conversaAtualId === null
      definirConversaAtualId(resultado.conversa_id)
      if (primeiraMensagemDaConversa) {
        recarregarConversas()
      }
    } catch (erroEnvio) {
      if (erroEnvio.status === 401) {
        aoSair()
        return
      }
      definirErro(erroEnvio.message)
    } finally {
      definirEnviando(false)
    }
  }

  return (
    <div className="conversa-layout">
      <Sidebar
        perfil={perfil}
        conversas={conversas}
        conversaAtualId={conversaAtualId}
        aoSelecionar={selecionarConversa}
        aoIniciarNova={iniciarNovaConversa}
        aoSair={aoSair}
      />

      <div className="conversa-painel">
        <BarraMais />

        {erro && (
          <p className="conversa-erro" role="alert">
            {erro}
          </p>
        )}

        <JanelaChat mensagens={mensagens} enviando={enviando} carregando={carregandoMensagens} />

        <CaixaDeEntrada aoEnviar={enviarMensagem} enviando={enviando} />
      </div>
    </div>
  )
}

export default Conversa
