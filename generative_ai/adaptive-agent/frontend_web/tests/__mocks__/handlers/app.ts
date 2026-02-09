import { http, HttpResponse } from 'msw'

export const appHandlers = [
  http.get('api/v1/welcome', () => {
    return HttpResponse.json({
      message: 'Welcome Engineer!'
    })
  }),
]
