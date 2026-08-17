import { useEffect, useRef } from 'react'
import Mensagem from './Mensagem.jsx'

function JanelaChat({ mensagens, enviando, carregando }) {
  const fimDaLista = useRef(null)

  useEffect(() => {
    fimDaLista.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [mensagens, enviando])

  if (carregando) {
    return (
      <div className="janela-chat" role="status">
        <p className="janela-chat-carregando">Carregando conversa...</p>
      </div>
    )
  }

  return (
    <div className="janela-chat">
      {mensagens.length === 0 && (
        <p className="janela-chat-vazia">
          Faça uma pergunta sobre os materiais do programa pra começar a conversa.
        </p>
      )}

      {mensagens.map((mensagem) => (
        <Mensagem key={mensagem.id} mensagem={mensagem} />
      ))}

      {enviando && (
        <div className="mensagem mensagem-agente" aria-live="polite">
          <span className="mensagem-avatar" aria-hidden="true">
            +
          </span>
          <div className="mensagem-corpo">
            <p className="mensagem-texto mensagem-digitando">Digitando...</p>
          </div>
        </div>
      )}

      <div ref={fimDaLista} />
    </div>
  )
}

export default JanelaChat
