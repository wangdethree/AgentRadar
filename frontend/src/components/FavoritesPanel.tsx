import { useEffect, useState } from 'react'

import { getFavorites, removeFavorite } from '../api/interactions'
import type { Favorite } from '../types/api'

interface FavoritesPanelProps {
  refreshKey: number
}

export function FavoritesPanel({ refreshKey }: FavoritesPanelProps) {
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getFavorites()
      .then(setFavorites)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : '收藏加载失败')
      })
  }, [refreshKey])

  async function handleRemove(id: number) {
    await removeFavorite(id)
    setFavorites((items) => items.filter((item) => item.id !== id))
  }

  return (
    <section className="dashboard-section" id="favorites">
      <div className="section-heading">
        <span>Saved research</span>
        <h2>收藏的项目</h2>
        <p>保留值得继续阅读、改造或用于面试演示的项目。</p>
      </div>
      {error && <p className="error-banner">{error}</p>}
      {!error && favorites.length === 0 && <p className="empty-state">还没有收藏项目。</p>}
      <div className="favorite-list">
        {favorites.map((favorite) => (
          <article key={favorite.id}>
            <div>
              <a href={favorite.repository.html_url} target="_blank" rel="noreferrer">
                {favorite.repository.full_name} ↗
              </a>
              <p>{favorite.note ?? favorite.repository.description ?? '等待添加研究备注'}</p>
            </div>
            <span>★ {favorite.repository.stars.toLocaleString()}</span>
            <button type="button" onClick={() => void handleRemove(favorite.id)}>移除</button>
          </article>
        ))}
      </div>
    </section>
  )
}

