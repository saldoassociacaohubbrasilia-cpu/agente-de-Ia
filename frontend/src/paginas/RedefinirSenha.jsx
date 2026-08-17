import { useState } from 'react'
import { redefinirSenha } from '../lib/api.js'
import BarraMais from '../componentes/BarraMais.jsx'
import './Login.css'

const TAMANHO_MIN_SENHA = 8

function RedefinirSenha({ token, aoConcluir }) {
  const [novaSenha, definirNovaSenha] = useState('')
  const [confirmacao, definirConfirmacao] = useState('')
  const [enviando, definirEnviando] = useState(false)
  const [concluido, definirConcluido] = useState(false)
  const [erro, definirErro] = useState('')

  async function aoEnviar(evento) {
    evento.preventDefault()
    definirErro('')

    if (novaSenha !== confirmacao) {
      definirErro('As senhas não coincidem.')
      return
    }
    if (novaSenha.length < TAMANHO_MIN_SENHA) {
      definirErro(`A senha precisa ter pelo menos ${TAMANHO_MIN_SENHA} caracteres.`)
      return
    }

    definirEnviando(true)
    try {
      await redefinirSenha(token, novaSenha)
      definirConcluido(true)
    } catch (erroRedefinicao) {
      definirErro(erroRedefinicao.message)
    } finally {
      definirEnviando(false)
    }
  }

  return (
    <div className="login-tela">
      <div className="login-cartao">
        <BarraMais />
        <div className="login-conteudo">
          <h1>Redefinir senha</h1>

          {concluido ? (
            <>
              <p className="login-mensagem-sucesso" role="status">
                Senha redefinida! Já pode entrar com a senha nova.
              </p>
              <button type="button" onClick={aoConcluir}>
                Ir pro login
              </button>
            </>
          ) : (
            <form onSubmit={aoEnviar} className="login-formulario">
              <label htmlFor="campo-nova-senha">Nova senha</label>
              <input
                id="campo-nova-senha"
                type="password"
                value={novaSenha}
                onChange={(evento) => definirNovaSenha(evento.target.value)}
                autoComplete="new-password"
                minLength={TAMANHO_MIN_SENHA}
                required
              />

              <label htmlFor="campo-confirmacao-senha">Confirme a senha nova</label>
              <input
                id="campo-confirmacao-senha"
                type="password"
                value={confirmacao}
                onChange={(evento) => definirConfirmacao(evento.target.value)}
                autoComplete="new-password"
                minLength={TAMANHO_MIN_SENHA}
                required
              />

              {erro && (
                <p className="login-erro" role="alert">
                  {erro}
                </p>
              )}

              <button type="submit" disabled={enviando}>
                {enviando ? 'Salvando...' : 'Salvar nova senha'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

export default RedefinirSenha
