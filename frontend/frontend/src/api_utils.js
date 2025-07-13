import axios from 'axios'
import env from 'react-dotenv'

// eslint-disable-next-line no-undef
const API_URL = env.API_URL

export const retrieveMessages = chatterId => axios.get(`${API_URL}/chatter/${chatterId}/messages`)

export const retrieveChatterId = nick => axios.get(`${API_URL}/chatter/${nick}/chatter_id`)

export const retrieveChattersOnStream = streamId => axios.get(`${API_URL}/stream/${streamId}/chatters`)

export const retrieveStreams = (creatorId, offset) => axios.get(`${API_URL}/streams?creator_id=${creatorId}&offset=${offset}`)

export const retrieveStreamComprehensive = streamId => axios.get(`${API_URL}/stream/${streamId}`)

export const retrieveChatterOnStreamMessages = (streamId, chatterId) => axios.get(`${API_URL}/stream/${streamId}/chatter/${chatterId}/messages`)

export const retrieveAllCreators = () => axios.get(`${API_URL}/creators`)
