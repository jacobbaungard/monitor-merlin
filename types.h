/*
 * Author: Andreas Ericsson <ae@op5.se>
 *
 * Copryight(C) 2005 OP5 AB
 * All rights reserved.
 *
 */

#ifndef TYPES_H
#define TYPES_H

/* for node->status */
#define STATE_NONE 0
#define STATE_PENDING 1
#define STATE_NEGOTIATING 2
#define STATE_CONNECTED 3

/** structures **/
struct node {
	char *name;
	int id;                 /* internal index lookup number */
	int sock;               /* the socket */
	int type;               /* server type (master, slave, loadbalanced) */
	int status;             /* status of this host (down, pending, active) */
	unsigned zread;         /* zero reads. 5 of those indicates closed con */
	unsigned selection;     /* numeric index for hostgroup */
	char *hostgroup;        /* only set for pollers on the noc-side */
	struct sockaddr *sa;    /* should always point to node->sain */
	struct sockaddr_in sain;
	unsigned short port;
	time_t last_recv;       /* last time node sent something to us */
	time_t last_sent;       /* when we sent something last */
	int last_action;        /* LA_CONNECT | LA_DISCONNECT | LA_HANDLED */
	int (*action)(struct node *, int); /* (daemon) action handler */
	struct node *next;      /* linked list (and tabulated) */
};

#endif /* TYPES_H */
