import { useState } from 'react'

function CaixaDeEntrada({ aoEnviar, enviando }) {
  const [texto, definirTexto] = useState('')

  function enviar() {
    const pergunta = texto.trim()
    if (!pergunta || enviando) return
    aoEnviar(pergunta)
    definirTexto('')
  }

  function aoEnviarFormulario(evento) {
    evento.preventDefault()
    enviar()
  }

  function aoApertarTecla(evento) {
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault()
      enviar()
    }
  }

  return (
    <form className="caixa-de-entrada" onSubmit={aoEnviarFormulario}>
      <label htmlFor="campo-pergunta" className="visualmente-oculto">
        Digite sua pergunta
      </label>
      <textarea
        id="campo-pergunta"
        value={texto}
        onChange={(evento) => definirTexto(evento.target.value)}
        onKeyDown={aoApertarTecla}
        placeholder="Digite sua pergunta sobre o programa..."
        rows={1}
        disabled={enviando}
      />
      <button type="submit" disabled={enviando || !texto.trim()}>
        Enviar
      </button>
    </form>
  )
}

export default CaixaDeEntrada
