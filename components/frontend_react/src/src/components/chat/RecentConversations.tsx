// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the License);
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import React, { useEffect } from "react"
import { fetchChatHistory } from "@/utils/api"
import { useQuery } from "@tanstack/react-query"
import { useQueryParams } from "@/utils/routing"
import dayjs from "dayjs"
import { Link } from "react-router-dom"
import Loading from "@/navigation/Loading"

interface RecentConversationsProps {
  token: string
}

const CHAT_DISPLAY_LIMIT = 4

const RecentConversations: React.FC<RecentConversationsProps> = ({ token }) => {
  const {
    isLoading,
    error,
    refetch,
    data: chatHistory,
  } = useQuery(["ChatHistory"], fetchChatHistory(token))

  const params = useQueryParams()
  const currChatId = params.get("chat_id")

  // Force fetch on chat ID change to display newly created chat
  useEffect(() => {
    if (currChatId) {
      refetch()
    }
  }, [currChatId])

  if (isLoading) return <></>
  if (error) return <></>
  if (!chatHistory?.length) return <Loading />

  const recentQueries = chatHistory
    .sort((a, b) => (b.created_time > a.created_time ? 1 : -1))
    .slice(0, CHAT_DISPLAY_LIMIT)

  return (
    <div className="border-primary-content mt-2 border-t p-2 py-3">
      <div className="text-primary-content pb-3 font-semibold">
        Recent Conversations
      </div>

      <div className="flex flex-col gap-4">
        {recentQueries.map((chat) => (
          <Link
            key={chat.id}
            className="border-primary-content text-primary-content hover:bg-primary-active flex cursor-pointer flex-col gap-1 rounded border-l-2 border-opacity-60 pl-2 opacity-80 transition"
            to={`/aichat?chat_id=${chat.id}`}
          >
            <div className="text-md truncate">{chat.prompt}</div>
            <div className="text-xs">
              {dayjs(chat.created_time).format("MMM D, YYYY • h:mm A")}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default RecentConversations
