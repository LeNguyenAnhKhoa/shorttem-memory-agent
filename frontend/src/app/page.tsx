"use client"

import React, { KeyboardEvent, useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Avatar } from "@/components/ui/avatar"
import { Send, ChevronDown, ChevronUp } from "lucide-react"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import Markdown from "react-markdown"

type PipelineStep = {
  type: string
  content: any
}

type Message = {
  id: number
  text: string
  sender: "user" | "assistant"
  pipelineSteps?: PipelineStep[]
  clarifyingQuestions?: string[]
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: "Hello! I'm your chat assistant with session memory. How can I help you today?", sender: "assistant" }
  ])
  const [newMessage, setNewMessage] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [typingMessage, setTypingMessage] = useState("")
  const [currentSteps, setCurrentSteps] = useState<PipelineStep[]>([])
  const [sessionId, setSessionId] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [openStates, setOpenStates] = useState<Record<number, boolean>>({})
  const [currentStepsOpen, setCurrentStepsOpen] = useState<boolean>(true)

  useEffect(() => {
    setSessionId(`session-${Date.now()}`)
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentSteps, openStates, currentStepsOpen])


  const toggleMessageSteps = (messageId: number) => {
    setOpenStates(current => ({
      ...current,
      [messageId]: !(current[messageId] ?? true)
    }))
  }

  const callChatAPI = async (userMessage: string) => {
    setIsLoading(true)
    setCurrentSteps([])
    setTypingMessage("")

    try {
      const requestBody = {
        query: userMessage,
        session_id: sessionId,
        messages: []
      }

      const apiUrl = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v0/chat/`;
      console.log("Calling API:", apiUrl);
      
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${process.env.NEXT_PUBLIC_BACKEND_API_KEY}`
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`)
      }

      if (!response.body) {
        throw new Error("ReadableStream not supported in this browser.")
      }

      // Read the stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder("utf-8")
      let buffer = ""
      let finalAnswer = ""
      let stepsCollected: PipelineStep[] = []
      let clarifyingQs: string[] = []

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true })

        // Split by newlines to get individual JSON objects
        const lines = buffer.split("\n")

        // Process all complete lines
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim()
          if (!line) continue // Skip empty lines

          try {
            const chunk = JSON.parse(line)

            // Process different chunk types
            if (chunk.type === "pipeline_step") {
              stepsCollected = [...stepsCollected, { type: "step", content: chunk.content }]
              setCurrentSteps([...stepsCollected])
            }
            else if (chunk.type === "summary") {
              stepsCollected = [...stepsCollected, { type: "summary", content: chunk.content }]
              setCurrentSteps([...stepsCollected])
            }
            else if (chunk.type === "query_understanding") {
              stepsCollected = [...stepsCollected, { type: "query_understanding", content: chunk.content }]
              setCurrentSteps([...stepsCollected])
            }
            else if (chunk.type === "clarifying_questions") {
              clarifyingQs = chunk.content
              stepsCollected = [...stepsCollected, { type: "clarifying_questions", content: chunk.content }]
              setCurrentSteps([...stepsCollected])
            }
            else if (chunk.type === "answer") {
              finalAnswer = chunk.content
              setTypingMessage(finalAnswer)
            }
          } catch (e) {
            console.error("Error processing chunk:", e, "Line:", line)
          }
        }

        // Keep the last partial line in the buffer
        buffer = lines[lines.length - 1]
      }

      // Add the final answer with steps to the messages
      if (finalAnswer) {
        const newMessageId = messages.length + 2

        setMessages(current => [...current, {
          id: newMessageId,
          text: finalAnswer,
          sender: "assistant",
          pipelineSteps: stepsCollected.length > 0 ? stepsCollected : undefined,
          clarifyingQuestions: clarifyingQs.length > 0 ? clarifyingQs : undefined
        }])

        if (stepsCollected.length > 0) {
          setOpenStates(current => ({
            ...current,
            [newMessageId]: false  // Collapsed by default
          }))
        }

      } else {
        const newMessageId = messages.length + 2

        setMessages(current => [...current, {
          id: newMessageId,
          text: `I have processed your request, but could not generate a proper response.`,
          sender: "assistant",
          pipelineSteps: stepsCollected.length > 0 ? stepsCollected : undefined
        }])
      }
    } catch (error) {
      console.error("Error calling chat API:", error)
      setMessages(current => [...current, {
        id: current.length + 1,
        text: "Sorry, there was an error processing your request. Please try again later.",
        sender: "assistant"
      }])
    } finally {
      setIsLoading(false)
      setTypingMessage("")
      setCurrentSteps([])
    }
  }

  const handleSendMessage = async () => {
    if (newMessage.trim() && !isLoading) {
      // Add user message to chat
      setMessages(current => [...current, {
        id: messages.length + 1,
        text: newMessage,
        sender: "user"
      }])

      const userMessage = newMessage
      setNewMessage("")

      // Call API with user message
      await callChatAPI(userMessage)
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSendMessage()
    }
  }

  // Format pipeline step for display
  const formatStepContent = (step: PipelineStep) => {
    if (step.type === "step") {
      return <div className="text-gray-600">📍 {step.content}</div>
    }
    if (step.type === "summary") {
      return (
        <div className="bg-blue-50 p-2 rounded">
          <div className="font-bold text-blue-700">📋 Session Summary Generated</div>
          <pre className="text-xs mt-1 overflow-x-auto">{JSON.stringify(step.content, null, 2)}</pre>
        </div>
      )
    }
    if (step.type === "query_understanding") {
      const qu = step.content
      return (
        <div className="bg-yellow-50 p-2 rounded">
          <div className="font-bold text-yellow-700">🔍 Query Analysis</div>
          <div className="text-xs mt-1">
            <div>Ambiguous: {qu.is_ambiguous ? "Yes" : "No"}</div>
            {qu.rewritten_query && <div>Rewritten: {qu.rewritten_query}</div>}
          </div>
        </div>
      )
    }
    if (step.type === "clarifying_questions") {
      return (
        <div className="bg-orange-50 p-2 rounded">
          <div className="font-bold text-orange-700">❓ Clarifying Questions</div>
          <ul className="text-xs mt-1 list-disc list-inside">
            {step.content.map((q: string, i: number) => <li key={i}>{q}</li>)}
          </ul>
        </div>
      )
    }
    return <div>{JSON.stringify(step.content)}</div>
  }

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto p-4 bg-gray-50">
      <div className="text-center mb-2 text-xs text-gray-400">Session: {sessionId}</div>
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            <div className="flex items-start gap-2 max-w-xs">
              {message.sender === "assistant" && (
                <Avatar className="h-8 w-8 bg-primary text-white flex items-center justify-center">
                  <span className="text-xs">AI</span>
                </Avatar>
              )}

              <div className="flex flex-col">

                {message.pipelineSteps && message.pipelineSteps.length > 0 && (
                  <Collapsible className="mb-1 w-full" open={openStates[message.id]} onOpenChange={() => toggleMessageSteps(message.id)}>
                    <CollapsibleTrigger asChild className="flex items-center text-xs text-gray-500 hover:text-gray-700 cursor-pointer">
                      <div className="flex items-center gap-1">
                        {(openStates[message.id] ?? false) ? (
                          <><ChevronUp className="h-3 w-3" /><span>Hide pipeline details ({message.pipelineSteps.length})</span></>
                        ) : (
                          <><ChevronDown className="h-3 w-3" /><span>Show pipeline details ({message.pipelineSteps.length})</span></>
                        )}
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="bg-gray-100 p-2 rounded-md mb-1 text-xs font-mono overflow-x-auto space-y-2">
                        {message.pipelineSteps.map((step, index) => (
                          <div key={index}>{formatStepContent(step)}</div>
                        ))}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                )}

                <Card className={`p-1 ${message.sender === "user" ? "bg-primary text-primary-foreground" : "bg-white"}`}>
                  <CardContent className="p-1">
                    <div className="text-sm text-justify">
                      <Markdown>
                        {message.text}
                      </Markdown>
                    </div>
                  </CardContent>
                </Card>

              </div>

              {message.sender === "user" && (
                <Avatar className="h-8 w-8 bg-gray-600 text-white flex items-center justify-center">
                  <span className="text-xs">U</span>
                </Avatar>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator with live pipeline display */}
        {(typingMessage || currentSteps.length > 0) && (
          <div className="flex justify-start">
            <div className="flex items-start gap-2 max-w-xs">
              <Avatar className="h-8 w-8 bg-primary text-white flex items-center justify-center mt-1">
                <span className="text-xs">AI</span>
              </Avatar>

              <div className="flex flex-col">

                {currentSteps.length > 0 && (
                  <Collapsible className="mb-1 w-full" open={currentStepsOpen} onOpenChange={setCurrentStepsOpen}>
                    <CollapsibleTrigger asChild className="flex items-center text-xs text-gray-500 hover:text-gray-700 cursor-pointer">
                      <div className="flex items-center gap-1">
                        {currentStepsOpen ? (
                          <><ChevronUp className="h-3 w-3" /><span>Hide pipeline details ({currentSteps.length})</span></>
                        ) : (
                          <><ChevronDown className="h-3 w-3" /><span>Show pipeline details ({currentSteps.length})</span></>
                        )}
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="bg-gray-100 p-2 rounded-md mb-1 text-xs font-mono overflow-x-auto space-y-2">
                        {currentSteps.map((step, index) => (
                          <div key={index}>{formatStepContent(step)}</div>
                        ))}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                )}

                {typingMessage && (
                  <Card className="p-1 bg-white">
                    <CardContent className="p-1">
                      <div className="text-sm text-justify">
                        <Markdown>
                          {typingMessage}
                        </Markdown>
                      </div>
                    </CardContent>
                  </Card>
                )}

              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef}></div>
      </div>

      <div className="flex gap-2">
        <Input
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Type your message here..."
          className="flex-1"
          disabled={isLoading}
        />
        <Button
          onClick={handleSendMessage}
          size="icon"
          disabled={isLoading || !newMessage.trim()}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
