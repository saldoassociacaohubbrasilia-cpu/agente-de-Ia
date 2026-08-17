import { useState } from 'react'
import { esqueciSenha } from '../lib/api.js'
import BarraMais from '../componentes/BarraMais.jsx'
import './Login.css'

function EsqueciSenha({ aoVoltar }) {
  const [usuario, definirUsuario] = useState('')
  const [enviando, definirEnviando] = useState(false)
  const [enviado, definirEnviado] = useState(false)
  const [erro, definirErro] = useState('')

  async function aoEnviar(evento) {
    evento.preventDefault()
    definirErro('')
    definirEnviando(true)
    try {
      await esqueciSenha(usuario)
      definirEnviado(true)
    } catch (erroPedido) {
      definirErro(erroPedido.message)
    } finally {
      definirEnviando(false)
    }
  }

  return (
    <div className="login-tela">
      <div className="login-cartao">
        <BarraMais />
        <div className="login-conteudo">
          <h1>Esqueci minha senha</h1>
          <p className="login-subtitulo">
            Informe seu usuário. Se ele existir, mandamos um link de redefinição pro e-mail cadastrado.
          </p>

          {enviado ? (
            <p className="login-mensagem-sucesso" role="status">
              Se o usuário existir, um e-mail com o link de redefinição foi enviado. Confira sua caixa de
              entrada (e o spam).
            </p>
          ) : (
            <form onSubmit={aoEnviar} className="login-formulario">
              <label htmlFor="campo-usuario-reset">Usuário</label>
              <input
                id="campo-usuario-reset"
                type="text"
                value={usuario}
                onChange={(evento) => definirUsuario(evento.target.value)}
                autoComplete="username"
                required
              />

              {erro && (
                <p className="login-erro" role="alert">
                  {erro}
                </p>
              )}

              <button type="submit" disabled={enviando}>
                {enviando ? 'Enviando...' : 'Enviar link de redefinição'}
              </button>
            </form>
          )}

          <button type="button" className="login-link-secundario" onClick={aoVoltar}>
            Voltar pro login
          </button>
        </div>
      </div>
    </div>
  )
}

export default EsqueciSenha
