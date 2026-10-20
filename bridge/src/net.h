// The connection to the Launcher client: a TCP server on 127.0.0.1:23850, so only this computer can connect, one
// client at a time (a second one gets {"type": "busy"} and is disconnected). Every message is a JSON object on one
// line. This module only moves lines: the game thread reads and answers them (bridge.cpp).
#pragma once
#include <string>
#include <vector>

namespace net {

const unsigned short kPort = 23850;

// Serves clients on the calling thread, forever. `hello` is the first line each new client gets
void Run(const std::string& hello);

// The lines received since the last call. `newClient` is set if a client connected since then
void TakeReceived(std::vector<std::string>& lines, bool& newClient);

// Queues a message for the client. It's dropped if no client is connected
void Send(const std::string& line);

bool Connected();

}  // namespace net
