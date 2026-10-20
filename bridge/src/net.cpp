#include "net.h"

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

#include "log.h"

namespace net {

namespace {

const size_t kMaxLine = 16 << 20;  // a longer message drops the client (16 MiB)
const int kWaitMs = 50;            // how long each round waits for the client
const char kBusy[] = "{\"type\":\"busy\"}";  // what a second client gets before it's disconnected

// Shared with the game thread, under the lock
SRWLOCK g_lock = SRWLOCK_INIT;
std::vector<std::string> g_received;
std::vector<std::string> g_toSend;
bool g_newClient = false;

volatile LONG g_connected = 0;

SOCKET Listen()
{
    SOCKET listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listener == INVALID_SOCKET) return listener;

    BOOL on = TRUE;
    setsockopt(listener, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, reinterpret_cast<const char*>(&on), sizeof(on));

    sockaddr_in address = {};
    address.sin_family = AF_INET;
    address.sin_port = htons(kPort);
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    if (bind(listener, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0 || listen(listener, 1) != 0) {
        closesocket(listener);
        return INVALID_SOCKET;
    }

    return listener;
}

bool SendAll(SOCKET socket, const std::string& data)
{
    for (size_t sent = 0; sent < data.size();) {
        int count = send(socket, data.data() + sent, static_cast<int>(data.size() - sent), 0);
        if (count <= 0) return false;

        sent += count;
    }

    return true;
}

void Close(SOCKET& client)
{
    closesocket(client);
    client = INVALID_SOCKET;
    InterlockedExchange(&g_connected, 0);
    Log("client disconnected");
}

// Takes a new connection and says hello. While a client is connected, a second one is turned away
void Accept(SOCKET listener, SOCKET& client, std::string& pending, const std::string& hello, bool& refusedLogged)
{
    SOCKET accepted = accept(listener, nullptr, nullptr);
    if (accepted == INVALID_SOCKET) return;

    if (client != INVALID_SOCKET) {
        if (!refusedLogged)
            Log("another client tried to connect: turned away");
        refusedLogged = true;

        SendAll(accepted, std::string(kBusy) + "\n");
        closesocket(accepted);
        return;
    }

    client = accepted;
    pending.clear();
    refusedLogged = false;

    BOOL on = TRUE;
    setsockopt(client, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&on), sizeof(on));

    // Nothing from an earlier connection carries over
    AcquireSRWLockExclusive(&g_lock);
    g_received.clear();
    g_toSend.clear();
    g_newClient = true;
    ReleaseSRWLockExclusive(&g_lock);

    InterlockedExchange(&g_connected, 1);
    Log("client connected");

    if (!SendAll(client, hello + "\n"))
        Close(client);
}

// Reads what the client sent and hands each complete line to the game thread
void Receive(SOCKET& client, std::string& pending)
{
    char chunk[1 << 16];
    int got = recv(client, chunk, sizeof(chunk), 0);
    if (got <= 0) {
        Close(client);
        return;
    }

    pending.append(chunk, got);

    std::vector<std::string> lines;
    size_t start = 0;
    for (size_t newline; (newline = pending.find('\n', start)) != std::string::npos; start = newline + 1) {
        size_t end = newline > start && pending[newline - 1] == '\r' ? newline - 1 : newline;
        if (end > start)
            lines.emplace_back(pending, start, end - start);
    }
    pending.erase(0, start);

    if (pending.size() > kMaxLine) {
        Log("a message longer than %u bytes: dropping the client", static_cast<unsigned>(kMaxLine));
        Close(client);
    }

    AcquireSRWLockExclusive(&g_lock);
    for (auto& line : lines)
        g_received.push_back(std::move(line));
    ReleaseSRWLockExclusive(&g_lock);
}

// Sends what the game thread queued. Without a client it's dropped
void Flush(SOCKET& client)
{
    std::vector<std::string> queued;
    AcquireSRWLockExclusive(&g_lock);
    queued.swap(g_toSend);
    ReleaseSRWLockExclusive(&g_lock);

    if (client == INVALID_SOCKET || queued.empty()) return;

    std::string data;
    for (const auto& line : queued)
        data += line + "\n";

    if (!SendAll(client, data))
        Close(client);
}

}  // namespace

void Run(const std::string& hello)
{
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);

    SOCKET listener = INVALID_SOCKET;
    SOCKET client = INVALID_SOCKET;
    std::string pending;  // received bytes that don't end in a newline yet
    bool refusedLogged = false;

    for (;;) {
        if (listener == INVALID_SOCKET) {
            listener = Listen();
            if (listener == INVALID_SOCKET) {
                Log("cannot listen on 127.0.0.1:%u (error %d), retrying in 5 s", kPort, WSAGetLastError());
                Sleep(5000);
                continue;
            }

            Log("listening on 127.0.0.1:%u", kPort);
        }

        fd_set readable;
        FD_ZERO(&readable);
        FD_SET(listener, &readable);
        if (client != INVALID_SOCKET)
            FD_SET(client, &readable);

        timeval wait = {0, kWaitMs * 1000};
        if (select(0, &readable, nullptr, nullptr, &wait) == SOCKET_ERROR) {
            Sleep(kWaitMs);
            continue;
        }

        if (FD_ISSET(listener, &readable))
            Accept(listener, client, pending, hello, refusedLogged);

        if (client != INVALID_SOCKET && FD_ISSET(client, &readable))
            Receive(client, pending);

        Flush(client);
    }
}

void TakeReceived(std::vector<std::string>& lines, bool& newClient)
{
    lines.clear();

    AcquireSRWLockExclusive(&g_lock);
    lines.swap(g_received);
    newClient = g_newClient;
    g_newClient = false;
    ReleaseSRWLockExclusive(&g_lock);
}

void Send(const std::string& line)
{
    if (!Connected()) return;

    AcquireSRWLockExclusive(&g_lock);
    g_toSend.push_back(line);
    ReleaseSRWLockExclusive(&g_lock);
}

bool Connected()
{
    return g_connected != 0;
}

}  // namespace net
