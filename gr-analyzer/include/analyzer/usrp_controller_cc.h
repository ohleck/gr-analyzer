/* -*- c++ -*- */
/*
 * Copyright 2015 <+YOU OR YOUR COMPANY+>.
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */


#ifndef INCLUDED_ANALYZER_USRP_CONTROLLER_CC_H
#define INCLUDED_ANALYZER_USRP_CONTROLLER_CC_H

#include <vector>

#include <analyzer/api.h>
#include <gnuradio/block.h>
#include <gnuradio/uhd/usrp_source.h>

namespace gr {
  namespace analyzer {

    /*!
     * \brief Control sweeping a URSP
     * \ingroup analyzer
     *
     */
    class ANALYZER_API usrp_controller_cc : virtual public gr::block
    {
     public:
      typedef boost::shared_ptr<usrp_controller_cc> sptr;

      /*!
       * \brief Return a shared_ptr to a new instance of analyzer::usrp_controller_cc.
       *
       * To avoid accidental use of raw pointers, analyzer::usrp_controller_cc's
       * constructor is in a private implementation
       * class. analyzer::usrp_controller_cc::make is the public interface for
       * creating new instances.
       */
      static sptr make(boost::shared_ptr<gr::uhd::usrp_source> &usrp,
                       std::vector<double> center_freqs,
                       double lo_offset,
                       size_t initial_delay,
                       size_t tune_delay,
                       size_t ncopy,
                       bool unittest=false);

      /*!
       * \brief Return true if flowgraph will exit at end of span
       */
      virtual bool get_exit_after_complete() = 0;

      /*!
       * \brief Exit the flowgraph at the end of the span.
       *
       * The end of the span means the block has copied a multiple of
       * ncopy*nsegments samples.
       */
      virtual void set_exit_after_complete() = 0;

      /*!
       * \brief Do not return WORK_DONE until set_exit_after_complete is called.
       */
      virtual void clear_exit_after_complete() = 0;
    };

  } // namespace analyzer
} // namespace gr

#endif /* INCLUDED_ANALYZER_USRP_CONTROLLER_CC_H */
